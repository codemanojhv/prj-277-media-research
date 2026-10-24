from __future__ import annotations

import asyncio
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Text, cast, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import RELEVANCE_THRESHOLD
from app.db.models import AppSetting, Article, ArticleAnalysis, Embedding, ProcessingJob, Source, Story, StoryArticle
from app.db.session import SessionLocal, get_db
from app.services.embeddings import EmbeddingProvider, cosine, lexical_embedding
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


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    rss_url: str = Field(min_length=8, max_length=2048)
    language: str = Field(default="en", min_length=2, max_length=12)
    region: str | None = Field(default=None, max_length=120)
    is_active: bool = True

    @field_validator("rss_url")
    @classmethod
    def public_http_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter a public HTTP or HTTPS RSS URL")
        return value.strip()

    @field_validator("language")
    @classmethod
    def supported_source_language(cls, value: str) -> str:
        if value not in LANGUAGE_LOCALES:
            raise ValueError("Choose one of the supported project languages")
        return value


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    rss_url: str | None = Field(default=None, min_length=8, max_length=2048)
    language: str | None = Field(default=None, min_length=2, max_length=12)
    region: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None

    @field_validator("rss_url")
    @classmethod
    def public_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter a public HTTP or HTTPS RSS URL")
        return value.strip()


class ScheduleUpdate(BaseModel):
    enabled: bool
    interval_minutes: int = Field(ge=15, le=10080)


class StoryUpdate(BaseModel):
    canonical_title: str = Field(min_length=1, max_length=500)
    summary: str = Field(default="", max_length=5000)


class StoryArticleRequest(BaseModel):
    article_id: int = Field(gt=0)


class StoryMergeRequest(BaseModel):
    other_story_id: int = Field(gt=0)


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
        evidence = dict(analysis.evidence or {})
        evidence.pop("stance", None)
        provider_decisions = evidence.get("provider_decisions")
        if isinstance(provider_decisions, dict):
            evidence["provider_decisions"] = {
                key: value for key, value in provider_decisions.items() if key != "stance"
            }
        data["analysis"] = {
            "goi_relevance_score": analysis.goi_relevance_score,
            "goi_relevance_threshold": RELEVANCE_THRESHOLD,
            "is_goi_relevant": analysis.is_goi_relevant,
            "relevance_reasons": analysis.relevance_reasons,
            "sentiment": analysis.sentiment,
            "sentiment_score": analysis.sentiment_score,
            "sentiment_confidence": analysis.sentiment_confidence,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "topics": analysis.topics,
            "entities": analysis.entities,
            "claims": analysis.claims,
            "concerns": analysis.concerns,
            "positive_aspects": analysis.positive_aspects,
            "evidence": evidence,
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
        "is_manually_curated": story.is_manually_curated,
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
            "main_topics": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(5)],
            "article_ids": [article.id for article in group],
        })
    return {
        "interpretation_note": "Descriptive comparison of the stored article sample. Topic and article-tone labels are model-derived and are not verified facts or a measure of outlet bias.",
        "shared_narrative": {"topics": shared_topics, "entities": shared_entities},
        "language_comparison": language_comparison,
        "source_comparison": source_comparison,
        "coverage_differences": differences[:12],
    }


def _apply_filters(
    statement, language, source_id, from_date, to_date, region,
    sentiment=None, topic=None, is_goi_relevant=None, is_synthetic=None,
):
    if language:
        statement = statement.where(Article.language == language)
    if source_id is not None:
        statement = statement.where(Article.source_id == source_id)
    if region:
        statement = statement.where(Article.region == region)
    if from_date:
        try:
            start = date.fromisoformat(from_date)
            statement = statement.where(Article.published_at >= datetime.combine(start, datetime.min.time(), UTC))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="from_date must be an ISO date") from exc
    if to_date:
        try:
            end = date.fromisoformat(to_date) + timedelta(days=1)
            statement = statement.where(Article.published_at < datetime.combine(end, datetime.min.time(), UTC))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="to_date must be an ISO date") from exc
    if sentiment:
        statement = statement.where(Article.id.in_(select(ArticleAnalysis.article_id).where(ArticleAnalysis.sentiment == sentiment)))
    if topic:
        pattern = topic.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Article.id.in_(
            select(ArticleAnalysis.article_id).where(cast(ArticleAnalysis.topics, Text).ilike(f"%{pattern}%", escape="\\"))
        ))
    if is_goi_relevant is not None:
        statement = statement.where(Article.id.in_(
            select(ArticleAnalysis.article_id).where(ArticleAnalysis.is_goi_relevant.is_(is_goi_relevant))
        ))
    if is_synthetic is not None:
        statement = statement.where(Article.is_synthetic.is_(is_synthetic))
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
        "topic_distribution": [{"label": key, "count": value} for key, value in topic_counts.most_common(8)],
        "articles_over_time": _articles_over_time(articles),
    }


@router.get("/analytics/breakdown")
def analytics_breakdown(
    dimension: str = "language",
    from_date: str | None = None,
    to_date: str | None = None,
    is_synthetic: bool | None = None,
    db: Session = Depends(get_db),
) -> dict:
    if dimension not in {"language", "source"}:
        raise HTTPException(status_code=422, detail="dimension must be 'language' or 'source'")
    statement = select(Article).join(Source).options(joinedload(Article.source), joinedload(Article.analysis))
    articles = list(db.scalars(_apply_filters(
        statement, None, None, from_date, to_date, None, is_synthetic=is_synthetic
    )).unique())
    groups: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        groups[article.language if dimension == "language" else article.source.name].append(article)
    items = []
    for label, group in groups.items():
        analyzed = [article.analysis for article in group if article.analysis]
        topic_counts = Counter(topic["topic"] for analysis in analyzed for topic in analysis.topics)
        items.append({
            "label": label,
            "sample_size": len(group),
            "languages": dict(Counter(article.language for article in group)),
            "sources": sorted({article.source.name for article in group}),
            "sentiment_distribution": dict(Counter(analysis.sentiment for analysis in analyzed)),
            "topic_distribution": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(8)],
            "article_ids": [article.id for article in group],
        })
    items.sort(key=lambda item: (-item["sample_size"], item["label"].casefold()))
    return {
        "dimension": dimension,
        "sample_size": len(articles),
        "items": items,
        "interpretation_note": "Counts describe only the selected stored sample. Model-derived article tone and topics are research aids, not verified facts or measures of outlet bias.",
    }


@router.get("/search")
def semantic_search(
    q: str = Query(min_length=2, max_length=200),
    language: str | None = None,
    source_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    region: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    is_goi_relevant: bool | None = None,
    is_synthetic: bool | None = None,
    story_id: int | None = None,
    research_job_id: int | None = None,
    limit: int = 25,
    db: Session = Depends(get_db),
) -> dict:
    statement = select(Embedding, Article).join(Article).join(Source).options(
        joinedload(Article.source), joinedload(Article.analysis)
    )
    statement = _apply_filters(
        statement, language, source_id, from_date, to_date, region, sentiment, topic,
        is_goi_relevant, is_synthetic,
    )
    if story_id is not None:
        statement = statement.where(Article.id.in_(select(StoryArticle.article_id).where(StoryArticle.story_id == story_id)))
    if research_job_id is not None:
        statement = statement.where(Article.research_job_id == research_job_id)
    rows = db.execute(statement).unique().all()
    if not rows:
        return {"query": q, "count": 0, "score_mode": "none", "items": []}

    model_name = Counter(embedding.embedding_model for embedding, _ in rows).most_common(1)[0][0]
    model_rows = [(embedding, article) for embedding, article in rows if embedding.embedding_model == model_name]
    score_mode = "semantic"
    if model_name.startswith("local-lexical"):
        score_mode = "lexical-fallback"
        query_vector = lexical_embedding(q)
    else:
        vectors, query_model = EmbeddingProvider(model_name).embed([q])
        if query_model == model_name:
            query_vector = vectors[0]
        else:
            score_mode = "lexical-fallback"
            query_terms = {term for term in re.findall(r"[\w]+", q.casefold()) if len(term) > 1}
            scored = []
            for _, article in rows:
                text = f"{article.title} {article.clean_content}".casefold()
                text_terms = set(re.findall(r"[\w]+", text))
                score = len(query_terms & text_terms) / len(query_terms) if query_terms else 0.0
                if score:
                    scored.append((score, article))
            scored.sort(key=lambda pair: (-pair[0], -(pair[1].published_at.timestamp() if pair[1].published_at else 0)))
            items = [{"score": round(score, 4), "article": article_card(article)} for score, article in scored[:max(1, min(limit, 50))]]
            return {"query": q, "count": len(scored), "score_mode": score_mode, "items": items}

    scored = [
        (cosine(query_vector, embedding.vector), article)
        for embedding, article in model_rows
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].published_at))
    items = [{"score": round(score, 4), "article": article_card(article)} for score, article in scored[:max(1, min(limit, 50))]]
    return {"query": q, "count": len(scored), "score_mode": score_mode, "items": items}


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
    sentiment: str | None = None,
    topic: str | None = None,
    is_goi_relevant: bool | None = None,
    is_synthetic: bool | None = None,
    research_job_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    matching = _apply_filters(
        select(Story.id).join(StoryArticle).join(Article), language, source_id, from_date, to_date, region,
        sentiment, topic, is_goi_relevant, is_synthetic,
    ).distinct()
    if research_job_id is not None:
        matching = matching.where(Article.research_job_id == research_job_id)
    ids = list(db.scalars(matching))
    stories = list(db.scalars(
        select(Story).where(Story.id.in_(ids)).options(selectinload(Story.article_links).joinedload(StoryArticle.article).joinedload(Article.source)).order_by(Story.last_updated.desc()).limit(limit).offset(offset)
    )) if ids else []
    return {"items": [story_card(story) for story in stories], "count": len(ids)}


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


@router.patch("/stories/{story_id}")
def update_story(story_id: int, request: StoryUpdate, db: Session = Depends(get_db)) -> dict:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    title = request.canonical_title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Story title cannot be blank")
    story.canonical_title = title
    story.summary = request.summary.strip()
    story.is_manually_curated = True
    db.commit()
    return {"id": story.id, "canonical_title": story.canonical_title, "is_manually_curated": True}


@router.post("/stories/{story_id}/articles")
def assign_article_to_story(story_id: int, request: StoryArticleRequest, db: Session = Depends(get_db)) -> dict:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not db.get(Article, request.article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    target_link = db.scalar(select(StoryArticle).where(
        StoryArticle.story_id == story_id, StoryArticle.article_id == request.article_id
    ))
    old_links = list(db.scalars(select(StoryArticle).where(StoryArticle.article_id == request.article_id)))
    for link in old_links:
        if link.story_id != story_id:
            db.delete(link)
    if target_link is None:
        db.add(StoryArticle(story_id=story_id, article_id=request.article_id, similarity_score=1.0))
    story.is_manually_curated = True
    db.commit()
    return {"story_id": story_id, "article_id": request.article_id, "is_manually_curated": True}


@router.delete("/stories/{story_id}/articles/{article_id}")
def remove_article_from_story(story_id: int, article_id: int, db: Session = Depends(get_db)) -> dict:
    story = db.get(Story, story_id)
    link = db.scalar(select(StoryArticle).where(
        StoryArticle.story_id == story_id, StoryArticle.article_id == article_id
    ))
    if not story or not link:
        raise HTTPException(status_code=404, detail="Story membership not found")
    story.is_manually_curated = True
    db.delete(link)
    db.flush()
    if not db.scalar(select(StoryArticle.id).where(StoryArticle.story_id == story_id).limit(1)):
        db.delete(story)
    db.commit()
    return {"story_id": story_id, "article_id": article_id, "removed": True}


@router.post("/stories/{story_id}/merge")
def merge_stories(story_id: int, request: StoryMergeRequest, db: Session = Depends(get_db)) -> dict:
    target = db.get(Story, story_id)
    source = db.get(Story, request.other_story_id)
    if not target or not source:
        raise HTTPException(status_code=404, detail="Story not found")
    if target.id == source.id:
        raise HTTPException(status_code=422, detail="Choose a different story to merge")
    target_articles = set(db.scalars(select(StoryArticle.article_id).where(StoryArticle.story_id == target.id)))
    for link in list(db.scalars(select(StoryArticle).where(StoryArticle.story_id == source.id))):
        if link.article_id in target_articles:
            db.delete(link)
        else:
            link.story_id = target.id
    target.is_manually_curated = True
    db.delete(source)
    db.commit()
    return {"id": target.id, "merged_story_id": request.other_story_id, "is_manually_curated": True}


@router.get("/articles")
def list_articles(
    language: str | None = None,
    source_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    region: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    is_goi_relevant: bool | None = None,
    is_synthetic: bool | None = None,
    story_id: int | None = None,
    research_job_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    statement = select(Article).join(Source).options(joinedload(Article.source), joinedload(Article.analysis)).order_by(Article.published_at.desc())
    statement = _apply_filters(
        statement, language, source_id, from_date, to_date, region, sentiment, topic,
        is_goi_relevant, is_synthetic,
    )
    if research_job_id is not None:
        statement = statement.where(Article.research_job_id == research_job_id)
    if story_id is not None:
        statement = statement.join(StoryArticle).where(StoryArticle.story_id == story_id)
    count_statement = select(func.count(Article.id))
    if story_id is not None:
        count_statement = count_statement.join(StoryArticle).where(StoryArticle.story_id == story_id)
    count_statement = _apply_filters(
        count_statement, language, source_id, from_date, to_date, region, sentiment, topic,
        is_goi_relevant, is_synthetic,
    )
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
    article_counts = dict(db.execute(select(Article.source_id, func.count(Article.id)).group_by(Article.source_id)))
    return {"items": [{
        "id": source.id, "name": source.name, "domain": source.domain, "language": source.language,
        "region": source.region, "source_type": source.source_type, "rss_url": source.rss_url,
        "is_active": source.is_active, "article_count": article_counts.get(source.id, 0),
    } for source in sources]}


@router.post("/sources", status_code=201)
def create_source(request: SourceCreate, db: Session = Depends(get_db)) -> dict:
    name = " ".join(request.name.split())
    if db.scalar(select(Source.id).where(func.lower(Source.name) == name.casefold())):
        raise HTTPException(status_code=409, detail="A source with this name already exists")
    source = Source(
        name=name, domain=urlparse(request.rss_url).hostname, language=request.language,
        region=request.region.strip() if request.region else None, source_type="rss",
        rss_url=request.rss_url, is_active=request.is_active,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "name": source.name, "rss_url": source.rss_url, "is_active": source.is_active}


@router.patch("/sources/{source_id}")
def update_source(source_id: int, request: SourceUpdate, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one source field to update")
    if updates.get("language") and updates["language"] not in LANGUAGE_LOCALES:
        raise HTTPException(status_code=422, detail="Choose one of the supported project languages")
    if "name" in updates:
        updates["name"] = " ".join((updates["name"] or "").split())
        if not updates["name"]:
            raise HTTPException(status_code=422, detail="Source name cannot be blank")
        duplicate = db.scalar(select(Source.id).where(
            func.lower(Source.name) == updates["name"].casefold(), Source.id != source_id
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail="A source with this name already exists")
    for field, value in updates.items():
        if field == "region":
            value = value.strip() if value else None
        if field == "rss_url" and value:
            source.domain = urlparse(value).hostname
        setattr(source, field, value)
    source.source_type = "rss" if source.rss_url else source.source_type
    db.commit()
    return {"id": source.id, "name": source.name, "rss_url": source.rss_url, "is_active": source.is_active}


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if db.scalar(select(Article.id).where(Article.source_id == source_id).limit(1)):
        raise HTTPException(status_code=409, detail="Sources with stored articles cannot be deleted; disable the feed instead")
    db.delete(source)
    db.commit()
    return {"id": source_id, "deleted": True}


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


def _run_source_collection_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        sources = list(db.scalars(select(Source).where(
            Source.is_active.is_(True), Source.rss_url.is_not(None)
        ).order_by(Source.name)))
        if not sources:
            job.status = "failed"
            job.error = "No active RSS sources are configured. Add a feed and enable it first."
            job.completed_at = datetime.now(UTC)
            db.commit()
            return

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.progress = 1
        db.commit()
        article_ids: list[int] = []
        warnings: list[str] = []
        successful_feeds = 0
        duplicates = 0
        for index, source in enumerate(sources, start=1):
            try:
                result = ingest_rss(db, source.rss_url or "", max_entries=8, source_name=source.name)
                successful_feeds += 1
                article_ids.extend(result["article_ids"])
                duplicates += result["duplicates"]
                warnings.extend(result.get("fetch_errors", []))
            except Exception as exc:
                warnings.append(f"{source.name}: {type(exc).__name__}: {exc}")
            job.progress = min(80, round(index * 80 / len(sources)))
            job.metadata_json = {"phase": f"Collected {index} of {len(sources)} feeds", "warnings": warnings[:20]}
            db.commit()

        pipeline_result = process_corpus(db, article_ids=article_ids) if article_ids else {
            "articles_processed": 0, "stories_created": 0, "embedding_model": "none",
        }
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        if successful_feeds == 0:
            job.status = "failed"
            job.error = "Every active RSS source failed to collect."
        else:
            job.status = "completed"
            job.progress = 100
        job.completed_at = datetime.now(UTC)
        job.metadata_json = {
            "feeds_checked": len(sources), "successful_feeds": successful_feeds,
            "created": len(article_ids), "duplicates": duplicates, "warnings": warnings[:20],
            **pipeline_result,
        }
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.completed_at = datetime.now(UTC)
            db.commit()
        print(f"[PIPELINE] collection job {job_id} failed: {type(exc).__name__}: {exc}")
    finally:
        db.close()


def _schedule_setting(db: Session) -> AppSetting:
    setting = db.get(AppSetting, "pipeline_schedule")
    if setting is None:
        setting = AppSetting(key="pipeline_schedule", value={"enabled": False, "interval_minutes": 1440, "next_run_at": None})
        db.add(setting)
        db.flush()
    return setting


@router.get("/pipeline/schedule")
def get_pipeline_schedule(db: Session = Depends(get_db)) -> dict:
    return dict(_schedule_setting(db).value)


@router.put("/pipeline/schedule")
def update_pipeline_schedule(request: ScheduleUpdate, db: Session = Depends(get_db)) -> dict:
    setting = _schedule_setting(db)
    next_run = datetime.now(UTC) + timedelta(minutes=request.interval_minutes) if request.enabled else None
    setting.value = {
        "enabled": request.enabled,
        "interval_minutes": request.interval_minutes,
        "next_run_at": next_run.isoformat() if next_run else None,
    }
    db.commit()
    return dict(setting.value)


@router.post("/pipeline/collect-sources", status_code=202)
def collect_sources(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    job = ProcessingJob(job_type="collect-rss-sources", status="queued", metadata_json={"phase": "Queued"})
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_source_collection_job, job.id)
    return {"id": job.id, "status": job.status, "status_url": f"/api/pipeline/jobs/{job.id}"}


@router.post("/pipeline/jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    previous = db.get(ProcessingJob, job_id)
    if not previous:
        raise HTTPException(status_code=404, detail="Processing job not found")
    if previous.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
    if previous.job_type not in {"process-and-cluster", "collect-rss-sources", "online-research"}:
        raise HTTPException(status_code=409, detail="This job type cannot be retried")
    metadata = dict(previous.metadata_json or {}) if previous.job_type == "online-research" else {}
    metadata.update({"phase": "Retry queued", "retry_of": previous.id})
    if previous.job_type == "online-research" and "request" not in metadata:
        raise HTTPException(status_code=409, detail="This research job has no saved request to retry")
    job = ProcessingJob(job_type=previous.job_type, status="queued", metadata_json=metadata)
    db.add(job)
    db.commit()
    db.refresh(job)
    runner = {
        "process-and-cluster": _run_pipeline_job,
        "collect-rss-sources": _run_source_collection_job,
        "online-research": _run_online_research_job,
    }[job.job_type]
    background_tasks.add_task(runner, job.id)
    return {"id": job.id, "status": job.status, "status_url": f"/api/pipeline/jobs/{job.id}"}


async def pipeline_scheduler() -> None:
    while True:
        job_id = None
        db = SessionLocal()
        try:
            setting = _schedule_setting(db)
            state = dict(setting.value or {})
            interval = max(15, min(10080, int(state.get("interval_minutes", 1440))))
            now = datetime.now(UTC)
            next_value = state.get("next_run_at")
            try:
                next_run = datetime.fromisoformat(next_value) if next_value else None
                if next_run and next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=UTC)
            except (TypeError, ValueError):
                next_run = None
            if state.get("enabled") and (next_run is None or next_run <= now):
                active = db.scalar(select(ProcessingJob.id).where(
                    ProcessingJob.job_type == "collect-rss-sources",
                    ProcessingJob.status.in_(("queued", "running")),
                ).limit(1))
                state["interval_minutes"] = interval
                state["next_run_at"] = (now + timedelta(minutes=interval)).isoformat()
                setting.value = state
                if active is None:
                    job = ProcessingJob(job_type="collect-rss-sources", status="queued", metadata_json={"phase": "Scheduled collection"})
                    db.add(job)
                    db.flush()
                    job_id = job.id
                db.commit()
        except Exception as exc:
            db.rollback()
            print(f"[SCHEDULER] {type(exc).__name__}: {exc}")
        finally:
            db.close()
        if job_id is not None:
            await asyncio.to_thread(_run_source_collection_job, job_id)
        await asyncio.sleep(30)


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
