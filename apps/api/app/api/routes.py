from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import RELEVANCE_THRESHOLD
from app.db.models import Article, ArticleAnalysis, ProcessingJob, Source, Story, StoryArticle
from app.db.session import SessionLocal, get_db
from app.services.ingestion import ingest_records, ingest_rss, ingest_url, parse_dataset
from app.services.jev import provider_status
from app.services.news_research import LANGUAGE_LOCALES, OUTLET_BY_ID, OUTLETS, collect_online_coverage
from app.services.pipeline import process_corpus

router = APIRouter(prefix="/api")


class URLRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class RSSRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    max_entries: int = Field(default=12, ge=1, le=30)


class OnlineResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    from_date: date
    to_date: date
    languages: list[str] = Field(default_factory=lambda: ["en"], min_length=1, max_length=5)
    outlet_ids: list[str] = Field(default_factory=list, max_length=12)
    per_language_limit: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        value = " ".join(value.split()).strip()
        if len(value) < 2:
            raise ValueError("Enter at least two characters for the topic")
        return value

    @field_validator("languages")
    @classmethod
    def supported_languages(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(values))
        unsupported = [value for value in result if value not in LANGUAGE_LOCALES]
        if unsupported:
            raise ValueError(f"Unsupported language selection: {', '.join(unsupported)}")
        return result

    @field_validator("outlet_ids")
    @classmethod
    def supported_outlets(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(values))
        unsupported = [value for value in result if value not in OUTLET_BY_ID]
        if unsupported:
            raise ValueError(f"Unsupported outlet selection: {', '.join(unsupported)}")
        return result

    @model_validator(mode="after")
    def valid_date_window(self):
        if self.from_date > self.to_date:
            raise ValueError("Start date must be on or before end date")
        if (self.to_date - self.from_date).days + 1 > 366:
            raise ValueError("Choose a date range of 366 days or less")
        return self


def _date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def article_card(article: Article) -> dict:
    analysis = article.analysis
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "source": {"id": article.source.id, "name": article.source.name, "domain": article.source.domain},
        "published_at": _date(article.published_at),
        "language": article.language,
        "language_confidence": article.language_confidence,
        "region": article.region,
        "is_synthetic": article.is_synthetic,
        "collection_method": article.collection_method,
        "content_kind": article.content_kind,
        "search_query": article.search_query,
        "discovery_url": article.discovery_url,
        "research_job_id": article.research_job_id,
        "goi_relevance": analysis.goi_relevance_score if analysis else 0.0,
        "sentiment": analysis.sentiment if analysis else "pending",
        "stance": analysis.stance if analysis else "pending",
        "topics": analysis.topics if analysis else [],
        "summary": analysis.summary if analysis else "Processing pending",
    }


def article_detail(article: Article) -> dict:
    data = article_card(article)
    data.update({
        "raw_content": article.raw_content,
        "content": article.clean_content,
        "author": article.author,
        "content_hash": article.content_hash,
        "collection_method": article.collection_method,
        "content_kind": article.content_kind,
        "search_query": article.search_query,
        "discovery_url": article.discovery_url,
        "research_job_id": article.research_job_id,
        "collected_at": _date(article.collected_at),
        "processed_at": _date(article.processed_at),
        "analysis": None,
    })
    if article.analysis:
        analysis = article.analysis
        data["analysis"] = {
            "goi_relevance_score": analysis.goi_relevance_score,
            "goi_relevance_threshold": RELEVANCE_THRESHOLD,
            "is_goi_relevant": analysis.is_goi_relevant,
            "relevance_reasons": analysis.relevance_reasons,
            "sentiment": analysis.sentiment,
            "sentiment_score": analysis.sentiment_score,
            "sentiment_confidence": analysis.sentiment_confidence,
            "stance": analysis.stance,
            "stance_target": analysis.stance_target,
            "stance_confidence": analysis.stance_confidence,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "topics": analysis.topics,
            "entities": analysis.entities,
            "claims": analysis.claims,
            "concerns": analysis.concerns,
            "positive_aspects": analysis.positive_aspects,
            "evidence": analysis.evidence,
            "model": analysis.model,
            "created_at": _date(analysis.created_at),
        }
    return data


def story_card(story: Story) -> dict:
    links = story.article_links
    articles = [link.article for link in links]
    return {
        "id": story.id,
        "canonical_title": story.canonical_title,
        "summary": story.summary,
        "article_count": len(articles),
        "languages": sorted({article.language for article in articles}),
        "sources": sorted({article.source.name for article in articles}),
        "first_seen": _date(story.first_seen),
        "last_updated": _date(story.last_updated),
        "goi_relevance": story.goi_relevance,
        "is_synthetic": any(article.is_synthetic for article in articles),
    }


def _comparison(articles: list[Article]) -> dict:
    analyzed = [article for article in articles if article.analysis]
    topic_sources: dict[str, list[int]] = defaultdict(list)
    entity_sources: dict[str, list[int]] = defaultdict(list)
    language_groups: dict[str, list[Article]] = defaultdict(list)
    source_groups: dict[str, list[Article]] = defaultdict(list)
    for article in analyzed:
        language_groups[article.language].append(article)
        source_groups[article.source.name].append(article)
        for topic in article.analysis.topics:
            topic_sources[topic["topic"]].append(article.id)
        for entity in article.analysis.entities:
            entity_sources[entity["text"]].append(article.id)
    shared_topics = [
        {"topic": topic, "article_ids": ids, "sample_count": len(ids)}
        for topic, ids in sorted(topic_sources.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(ids) >= 2
    ][:6]
    shared_entities = [
        {"entity": entity, "article_ids": ids, "sample_count": len(ids)}
        for entity, ids in sorted(entity_sources.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(ids) >= 2
    ][:6]
    language_comparison = []
    for language, group in sorted(language_groups.items()):
        topic_counts = Counter(topic["topic"] for article in group for topic in article.analysis.topics)
        language_comparison.append({
            "language": language,
            "sample_size": len(group),
            "sources": sorted({article.source.name for article in group}),
            "sentiment_distribution": dict(Counter(article.analysis.sentiment for article in group)),
            "stance_distribution": dict(Counter(article.analysis.stance for article in group)),
            "main_topics": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(5)],
            "article_ids": [article.id for article in group],
        })
    differences = []
    for left_index, left in enumerate(language_comparison):
        for right in language_comparison[left_index + 1:]:
            left_topics = {item["topic"] for item in left["main_topics"]}
            right_topics = {item["topic"] for item in right["main_topics"]}
            left_only = sorted(left_topics - right_topics)
            right_only = sorted(right_topics - left_topics)
            if left_only or right_only:
                differences.append({
                    "dimension": "topic emphasis",
                    "group_a": left["language"],
                    "group_b": right["language"],
                    "difference": f"The observed sample includes {', '.join(left_only) or 'no unique top topic'} in {left['language']} coverage and {', '.join(right_only) or 'no unique top topic'} in {right['language']} coverage.",
                    "sample_sizes": {left["language"]: left["sample_size"], right["language"]: right["sample_size"]},
                    "article_ids": left["article_ids"] + right["article_ids"],
                })
    source_comparison = []
    for source_name, group in sorted(source_groups.items()):
        topic_counts = Counter(topic["topic"] for article in group for topic in article.analysis.topics)
        source_comparison.append({
            "source": source_name,
            "language": group[0].language,
            "sample_size": len(group),
            "sentiment_distribution": dict(Counter(article.analysis.sentiment for article in group)),
            "stance_distribution": dict(Counter(article.analysis.stance for article in group)),
            "main_topics": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(5)],
            "article_ids": [article.id for article in group],
        })
    return {
        "interpretation_note": "Descriptive comparison of the stored article sample. Topic, sentiment, and stance values are model-derived and are not verified facts or a measure of outlet bias.",
        "shared_narrative": {"topics": shared_topics, "entities": shared_entities},
        "language_comparison": language_comparison,
        "source_comparison": source_comparison,
        "coverage_differences": differences[:12],
    }


def _apply_filters(statement, language, source_id, from_date, to_date, region):
    if language:
        statement = statement.where(Article.language == language)
    if source_id is not None:
        statement = statement.where(Article.source_id == source_id)
    if region:
        statement = statement.where(Article.region == region)
    if from_date:
        try:
            statement = statement.where(Article.published_at >= datetime.fromisoformat(from_date))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="from_date must be an ISO date") from exc
    if to_date:
        try:
            statement = statement.where(Article.published_at < datetime.fromisoformat(to_date).replace(hour=23, minute=59, second=59))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="to_date must be an ISO date") from exc
    return statement


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "prj-277-api"}


@router.get("/analysis/provider")
def analysis_provider() -> dict:
    """Expose safe provider configuration status without returning credentials."""
    return provider_status()


@router.get("/analytics/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    articles = list(db.scalars(select(Article).options(joinedload(Article.source), joinedload(Article.analysis))))
    stories = db.scalar(select(func.count(Story.id))) or 0
    sources = db.scalar(select(func.count(Source.id))) or 0
    languages = Counter(article.language for article in articles)
    by_source = Counter(article.source.name for article in articles)
    sentiments = Counter(article.analysis.sentiment for article in articles if article.analysis)
    stances = Counter(article.analysis.stance for article in articles if article.analysis)
    topic_counts = Counter(
        topic["topic"] for article in articles if article.analysis for topic in article.analysis.topics
    )
    relevant = sum(bool(article.analysis and article.analysis.is_goi_relevant) for article in articles)
    return {
        "total_articles": len(articles),
        "relevant_articles": relevant,
        "story_clusters": stories,
        "sources": sources,
        "languages": len(languages),
        "topics_detected": len(topic_counts),
        "synthetic_articles": sum(article.is_synthetic for article in articles),
        "by_language": [{"label": key, "count": value} for key, value in sorted(languages.items())],
        "by_source": [{"label": key, "count": value} for key, value in by_source.most_common(8)],
        "sentiment_distribution": [{"label": key, "count": value} for key, value in sentiments.most_common()],
        "stance_distribution": [{"label": key, "count": value} for key, value in stances.most_common()],
        "topic_distribution": [{"label": key, "count": value} for key, value in topic_counts.most_common(8)],
        "articles_over_time": _articles_over_time(articles),
    }


@router.get("/research/options")
def research_options() -> dict:
    today = datetime.now(UTC).date()
    return {
        "languages": [{"code": code, "label": value["label"]} for code, value in LANGUAGE_LOCALES.items()],
        "outlets": OUTLETS,
        "default_from_date": (today - timedelta(days=29)).isoformat(),
        "default_to_date": today.isoformat(),
        "providers": ["Google News RSS", "Bing News RSS"],
        "requires_api_key": False,
        "maximum_date_range_days": 366,
        "maximum_articles_per_language": 10,
    }


@router.post("/research/search", status_code=202)
def start_online_research(
    request: OnlineResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    job = ProcessingJob(
        job_type="online-research",
        status="queued",
        metadata_json={"request": request.model_dump(mode="json"), "phase": "Queued"},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_online_research_job, job.id)
    return {"id": job.id, "status": job.status, "status_url": f"/api/research/jobs/{job.id}"}


@router.get("/research/jobs")
def list_research_jobs(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    jobs = list(db.scalars(
        select(ProcessingJob)
        .where(ProcessingJob.job_type == "online-research")
        .order_by(ProcessingJob.id.desc())
        .limit(max(1, min(limit, 50)))
    ))
    return {"items": [_job_data(job) for job in jobs], "count": len(jobs)}


@router.get("/research/jobs/{job_id}")
def get_research_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(ProcessingJob, job_id)
    if not job or job.job_type != "online-research":
        raise HTTPException(status_code=404, detail="Online research job not found")
    return _job_data(job)


def _run_online_research_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        request = OnlineResearchRequest.model_validate(job.metadata_json["request"])
        job.status = "running"
        job.progress = 2
        job.started_at = datetime.now(UTC)
        job.metadata_json = {**job.metadata_json, "phase": "Starting online search"}
        db.commit()

        def update_progress(value: int, phase: str = "Processing online coverage") -> None:
            current = db.get(ProcessingJob, job_id)
            if current:
                current.progress = max(current.progress, min(99, value))
                current.metadata_json = {**current.metadata_json, "phase": phase}
                db.commit()

        result = collect_online_coverage(
            db,
            query=request.query,
            aliases=request.aliases,
            from_date=request.from_date,
            to_date=request.to_date,
            languages=request.languages,
            outlet_ids=request.outlet_ids,
            per_language_limit=request.per_language_limit,
            job_id=job_id,
            progress=update_progress,
        )
        article_ids = result.get("article_ids", [])
        if article_ids:
            pipeline_result = process_corpus(
                db,
                article_ids=article_ids,
                progress=lambda value: update_progress(55 + round(value * 0.44), "Analyzing, embedding, and clustering collected articles"),
            )
            result.update(pipeline_result)
            result["story_ids"] = list(db.scalars(
                select(Story.id).join(StoryArticle).where(StoryArticle.article_id.in_(article_ids)).distinct()
            ))
        else:
            result.update({"articles_processed": 0, "stories_created": 0, "embedding_model": "none", "story_ids": []})
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            job.metadata_json = {"request": request.model_dump(mode="json"), "phase": "Complete", "result": result}
            db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.completed_at = datetime.now(UTC)
            job.metadata_json = {**job.metadata_json, "phase": "Search or analysis failed"}
            db.commit()
        print(f"[ONLINE RESEARCH] job {job_id} failed: {type(exc).__name__}: {exc}")
    finally:
        db.close()


def _articles_over_time(articles: list[Article]) -> list[dict]:
    counts = Counter(article.published_at.strftime("%Y-%m-%d") for article in articles)
    return [{"date": key, "count": count} for key, count in sorted(counts.items())[-14:]]


@router.get("/stories")
def list_stories(
    language: str | None = None,
    source_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    region: str | None = None,
    research_job_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 200))
    matching = _apply_filters(select(Story.id).join(StoryArticle).join(Article), language, source_id, from_date, to_date, region).distinct()
    if research_job_id is not None:
        matching = matching.where(Article.research_job_id == research_job_id)
    ids = list(db.scalars(matching))
    stories = list(db.scalars(
        select(Story).where(Story.id.in_(ids)).options(selectinload(Story.article_links).joinedload(StoryArticle.article).joinedload(Article.source)).order_by(Story.last_updated.desc()).limit(limit)
    )) if ids else []
    return {"items": [story_card(story) for story in stories], "count": len(stories)}


@router.get("/stories/{story_id}")
def get_story(story_id: int, db: Session = Depends(get_db)) -> dict:
    story = db.scalar(select(Story).where(Story.id == story_id).options(
        selectinload(Story.article_links).joinedload(StoryArticle.article).joinedload(Article.source),
        selectinload(Story.article_links).joinedload(StoryArticle.article).joinedload(Article.analysis),
    ))
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    articles = [link.article for link in story.article_links]
    return {
        **story_card(story),
        "articles": [article_card(article) for article in sorted(articles, key=lambda item: item.published_at, reverse=True)],
        "comparison": _comparison(articles),
    }


@router.get("/articles")
def list_articles(
    language: str | None = None,
    source_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    region: str | None = None,
    story_id: int | None = None,
    research_job_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    statement = select(Article).join(Source).options(joinedload(Article.source), joinedload(Article.analysis)).order_by(Article.published_at.desc())
    statement = _apply_filters(statement, language, source_id, from_date, to_date, region)
    if research_job_id is not None:
        statement = statement.where(Article.research_job_id == research_job_id)
    if story_id is not None:
        statement = statement.join(StoryArticle).where(StoryArticle.story_id == story_id)
    count_statement = select(func.count(Article.id))
    if story_id is not None:
        count_statement = count_statement.join(StoryArticle).where(StoryArticle.story_id == story_id)
    count_statement = _apply_filters(count_statement, language, source_id, from_date, to_date, region)
    if research_job_id is not None:
        count_statement = count_statement.where(Article.research_job_id == research_job_id)
    items = list(db.scalars(statement.limit(max(1, min(limit, 200))).offset(max(0, offset))).unique())
    return {"items": [article_card(article) for article in items], "count": db.scalar(count_statement) or 0}


@router.get("/articles/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)) -> dict:
    article = db.scalar(select(Article).where(Article.id == article_id).options(joinedload(Article.source), joinedload(Article.analysis)))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    result = article_detail(article)
    link = db.scalar(select(StoryArticle).where(StoryArticle.article_id == article.id))
    if link:
        story = db.get(Story, link.story_id)
        result["story"] = {"id": story.id, "canonical_title": story.canonical_title} if story else None
    return result


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> dict:
    sources = list(db.scalars(select(Source).order_by(Source.name)))
    return {"items": [{"id": source.id, "name": source.name, "domain": source.domain, "language": source.language, "region": source.region, "source_type": source.source_type} for source in sources]}


@router.get("/languages")
def list_languages(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(Article.language, func.count(Article.id)).group_by(Article.language).order_by(Article.language))
    return {"items": [{"language": language, "count": count} for language, count in rows]}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)) -> dict:
    topics = Counter(topic["topic"] for row in db.scalars(select(ArticleAnalysis)) for topic in row.topics)
    return {"items": [{"topic": topic, "count": count} for topic, count in topics.most_common()]}


@router.post("/ingestion/dataset")
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    filename = Path(file.filename or "dataset.json").name
    if not filename.lower().endswith((".json", ".csv")):
        raise HTTPException(status_code=415, detail="Upload a UTF-8 JSON or CSV dataset")
    content = await file.read(5 * 1024 * 1024 + 1)
    try:
        records = parse_dataset(filename, content)
        result = ingest_records(db, records)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["received"] = len(records)
    return result


@router.post("/ingestion/url")
def ingest_single_url(request: URLRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return ingest_url(db, request.url)
    except (ValueError, OSError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=f"Article could not be collected: {exc}") from exc


@router.post("/ingestion/rss")
def ingest_feed(request: RSSRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return ingest_rss(db, request.url, request.max_entries)
    except (ValueError, OSError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=f"RSS feed could not be collected: {exc}") from exc


def _run_pipeline_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        db.commit()

        def update_progress(value: int) -> None:
            current = db.get(ProcessingJob, job_id)
            if current:
                current.progress = value
                db.commit()

        result = process_corpus(db, progress=update_progress)
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            job.metadata_json = result
            db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.completed_at = datetime.now(UTC)
            db.commit()
        print(f"[PIPELINE] job {job_id} failed: {type(exc).__name__}: {exc}")
    finally:
        db.close()


@router.post("/pipeline/run", status_code=202)
def start_pipeline(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    job = ProcessingJob(job_type="process-and-cluster", status="queued", metadata_json={})
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_pipeline_job, job.id)
    return {"id": job.id, "status": job.status, "status_url": f"/api/pipeline/jobs/{job.id}"}


@router.get("/pipeline/jobs")
def list_jobs(limit: int = 50, db: Session = Depends(get_db)) -> dict:
    jobs = list(db.scalars(select(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(max(1, min(limit, 100)))))
    return {"items": [_job_data(job) for job in jobs]}


@router.get("/pipeline/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return _job_data(job)


def _job_data(job: ProcessingJob) -> dict:
    return {
        "id": job.id, "job_type": job.job_type, "status": job.status, "progress": job.progress,
        "started_at": _date(job.started_at), "completed_at": _date(job.completed_at), "error": job.error,
        "metadata": job.metadata_json,
    }
