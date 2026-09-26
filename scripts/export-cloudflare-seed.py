from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import joinedload  # noqa: E402

from app.db.models import Article, Story, StoryArticle  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return "'" + str(value).replace("'", "''").replace("\x00", "") + "'"


def values_sql(values: list[Any]) -> str:
    return "(" + ", ".join(sql_value(value) for value in values) + ")"


def insert(table: str, columns: list[str], values: list[Any]) -> str:
    column_sql = ", ".join(columns)
    return f"INSERT OR IGNORE INTO {table} ({column_sql}) VALUES {values_sql(values)};"


def main() -> None:
    output = PROJECT_ROOT / "apps" / "web" / "cloudflare" / "demo_seed.sql"
    db = SessionLocal()
    try:
        articles = list(
            db.scalars(
                select(Article)
                .where(Article.is_synthetic.is_(True))
                .options(joinedload(Article.source), joinedload(Article.analysis), joinedload(Article.story_links))
                .order_by(Article.id)
            ).unique()
        )
        if len(articles) < 100 or any(article.analysis is None for article in articles):
            raise SystemExit(
                "Cloudflare seed needs the processed 100-article synthetic corpus. Run `npm run demo` once, "
                "let its seed pipeline finish, then rerun this command."
            )

        article_ids = {article.id for article in articles}
        story_ids = {
            link.story_id
            for article in articles
            for link in article.story_links
        }
        source_ids = {article.source_id for article in articles}
        sources = {
            source.id: source
            for source in db.scalars(select(Article.source.property.mapper.class_)).all()
            if source.id in source_ids
        }
        stories = {
            story.id: story
            for story in db.scalars(select(Story).where(Story.id.in_(story_ids))).all()
        }
        links = list(
            db.scalars(
                select(StoryArticle)
                .where(StoryArticle.article_id.in_(article_ids), StoryArticle.story_id.in_(story_ids))
                .order_by(StoryArticle.id)
            )
        )

        statements = ["-- Synthetic PRJ_277 classroom seed. No live reporting is included."]
        for source in sources.values():
            statements.append(
                insert(
                    "sources",
                    ["id", "name", "domain", "language", "region", "source_type", "rss_url", "created_at"],
                    [source.id, source.name, source.domain, source.language, source.region, source.source_type, source.rss_url, source.created_at],
                )
            )
        for story in stories.values():
            statements.append(
                insert(
                    "stories",
                    ["id", "cluster_key", "canonical_title", "summary", "goi_relevance", "first_seen", "last_updated", "created_at"],
                    [
                        story.id,
                        f"synthetic:{story.id}",
                        story.canonical_title,
                        story.summary,
                        story.goi_relevance,
                        story.first_seen,
                        story.last_updated,
                        story.created_at,
                    ],
                )
            )
        for article in articles:
            statements.append(
                insert(
                    "articles",
                    [
                        "id", "source_id", "url", "title", "raw_content", "clean_content", "author", "published_at",
                        "language", "language_confidence", "region", "content_hash", "is_synthetic", "collection_method",
                        "content_kind", "search_query", "discovery_url", "research_job_id", "collected_at", "processed_at",
                    ],
                    [
                        article.id, article.source_id, article.url, article.title, article.raw_content, article.clean_content,
                        article.author, article.published_at, article.language, article.language_confidence, article.region,
                        article.content_hash, article.is_synthetic, article.collection_method, article.content_kind,
                        article.search_query, article.discovery_url, article.research_job_id, article.collected_at, article.processed_at,
                    ],
                )
            )
            analysis = article.analysis
            statements.append(
                insert(
                    "article_analysis",
                    [
                        "article_id", "goi_relevance_score", "is_goi_relevant", "relevance_reasons", "sentiment",
                        "sentiment_score", "sentiment_confidence", "stance", "stance_target", "stance_confidence", "summary",
                        "key_points", "topics", "entities", "claims", "concerns", "positive_aspects", "evidence", "model", "created_at",
                    ],
                    [
                        article.id, analysis.goi_relevance_score, analysis.is_goi_relevant, analysis.relevance_reasons,
                        analysis.sentiment, analysis.sentiment_score, analysis.sentiment_confidence, analysis.stance,
                        analysis.stance_target, analysis.stance_confidence, analysis.summary, analysis.key_points, analysis.topics,
                        analysis.entities, analysis.claims, analysis.concerns, analysis.positive_aspects, analysis.evidence,
                        analysis.model, analysis.created_at,
                    ],
                )
            )
        for link in links:
            statements.append(
                insert(
                    "story_articles",
                    ["id", "story_id", "article_id", "similarity_score"],
                    [link.id, link.story_id, link.article_id, link.similarity_score],
                )
            )
        statements.append("INSERT OR REPLACE INTO app_meta (key, value) VALUES ('synthetic_seed_v1', 'loaded');")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(statements) + "\n", encoding="utf-8")
        print(f"Wrote {output.relative_to(PROJECT_ROOT)} with {len(articles)} synthetic articles.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
