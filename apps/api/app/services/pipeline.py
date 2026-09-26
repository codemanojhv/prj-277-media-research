from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import RELEVANCE_THRESHOLD
from app.db.models import Article, ArticleAnalysis, Embedding, Story, StoryArticle
from app.services import gemini as gemini_service
from app.services import jev as jev_service
from app.services.analysis import analyze_article
from app.services.embeddings import EmbeddingProvider, cosine, enrich_for_embedding, matched_concepts
from app.services.language import detect_language
from app.services.relevance import assess_relevance


def _union_find(size: int):
    parent = list(range(size))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    return find, union


def process_corpus(db: Session, progress=None, article_ids: list[int] | None = None) -> dict:
    statement = select(Article).options(joinedload(Article.source), joinedload(Article.analysis)).order_by(Article.id)
    if article_ids is not None:
        if not article_ids:
            return {"articles_processed": 0, "stories_created": 0, "embedding_model": "none"}
        statement = statement.where(Article.id.in_(article_ids))
    articles = list(db.scalars(statement))
    if not articles:
        return {"articles_processed": 0, "stories_created": 0, "embedding_model": "none"}
    has_real_articles = any(not article.is_synthetic for article in articles)
    use_external_provider = jev_service.config.ANALYSIS_PROVIDER != "local" and has_real_articles
    decision_provider = jev_service.configured_jev_provider() if use_external_provider else None
    text_provider = gemini_service.configured_gemini_provider() if has_real_articles else None
    texts: list[str] = []
    for index, article in enumerate(articles, start=1):
        language, confidence = detect_language(article.clean_content, article.language)
        article.language = language
        article.language_confidence = confidence
        relevance = assess_relevance(f"{article.title} {article.clean_content}", RELEVANCE_THRESHOLD)
        result = analyze_article(article.clean_content, language)
        if decision_provider is not None and not article.is_synthetic:
            decisions = decision_provider.classify_article(article.title, article.clean_content, language)
            result, relevance = jev_service.apply_jev_decisions(
                result, relevance, decisions, jev_service.config.JEV_MIN_CONFIDENCE
            )
        if text_provider is not None and not article.is_synthetic:
            try:
                generated = text_provider.generate_summary(article.title, article.clean_content, language)
                result = gemini_service.apply_gemini_summary(result, generated)
            except gemini_service.GeminiProviderError as exc:
                result["evidence"] = {
                    **result.get("evidence", {}),
                    "gemini_note": f"{exc} Local extracted summary was used.",
                }
        analysis = article.analysis
        if analysis is None:
            analysis = ArticleAnalysis(article_id=article.id)
            db.add(analysis)
            article.analysis = analysis
        analysis.goi_relevance_score = relevance["score"]
        analysis.is_goi_relevant = relevance["is_relevant"]
        analysis.relevance_reasons = relevance["reasons"]
        for name in (
            "sentiment", "sentiment_score", "sentiment_confidence", "stance", "stance_target", "stance_confidence",
            "summary", "key_points", "topics", "entities", "claims", "concerns", "positive_aspects", "evidence", "model",
        ):
            setattr(analysis, name, result[name])
        article.processed_at = datetime.now(UTC)
        texts.append(enrich_for_embedding(f"{article.title}. {article.clean_content}"))
        if progress and index % 10 == 0:
            progress(round(index * 70 / len(articles)))
    db.flush()

    provider = EmbeddingProvider()
    vectors, embedding_model = provider.embed(texts)
    for article, vector in zip(articles, vectors, strict=True):
        embedding = db.scalar(select(Embedding).where(Embedding.article_id == article.id))
        if embedding is None:
            embedding = Embedding(article_id=article.id, embedding_model=embedding_model, vector=vector)
            db.add(embedding)
        else:
            embedding.embedding_model = embedding_model
            embedding.vector = vector
    db.flush()

    if article_ids is None:
        db.execute(delete(StoryArticle))
        db.execute(delete(Story))
    else:
        # Online research jobs build story clusters only from the articles they collected.
        # Existing synthetic data and prior research runs remain intact.
        db.execute(delete(StoryArticle).where(StoryArticle.article_id.in_(article_ids)))
    find, union = _union_find(len(articles))
    edge_scores: dict[tuple[int, int], float] = {}
    dense = not embedding_model.startswith("local-lexical")
    threshold = 0.61 if dense else 0.53
    for left in range(len(articles)):
        for right in range(left + 1, len(articles)):
            score = cosine(vectors[left], vectors[right])
            left_concepts = set(matched_concepts(texts[left]))
            right_concepts = set(matched_concepts(texts[right]))
            shared_concepts = left_concepts & right_concepts
            if left_concepts and right_concepts and not shared_concepts:
                continue
            pair_threshold = threshold if shared_concepts else 0.91
            if score >= pair_threshold:
                union(left, right)
                edge_scores[(left, right)] = score
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(articles)):
        groups[find(index)].append(index)

    for member_indexes in groups.values():
        members = [articles[index] for index in member_indexes]
        english = next((article for article in members if article.language == "en"), None)
        representative = english or members[0]
        analysis = representative.analysis
        relevance_scores = [article.analysis.goi_relevance_score for article in members if article.analysis]
        first_seen = min(article.published_at for article in members)
        last_updated = max(article.published_at for article in members)
        story = Story(
            canonical_title=representative.title,
            summary=analysis.summary if analysis else "",
            goi_relevance=max(relevance_scores, default=0.0),
            first_seen=first_seen,
            last_updated=last_updated,
        )
        db.add(story)
        db.flush()
        for index, article in zip(member_indexes, members, strict=True):
            nearest = max(
                (edge_scores.get((min(index, other), max(index, other)), 0.0) for other in member_indexes if other != index),
                default=1.0,
            )
            db.add(StoryArticle(story_id=story.id, article_id=article.id, similarity_score=max(nearest, 1.0 if len(members) == 1 else 0.0)))
    db.commit()
    if progress:
        progress(100)
    return {"articles_processed": len(articles), "stories_created": len(groups), "embedding_model": embedding_model}
