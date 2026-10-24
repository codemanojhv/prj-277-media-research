from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(UTC)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(12), index=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="news")
    rss_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    articles: Mapped[list[Article]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    raw_content: Mapped[str] = mapped_column(Text)
    clean_content: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    language: Mapped[str] = mapped_column(String(12), index=True)
    language_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    collection_method: Mapped[str] = mapped_column(String(40), default="dataset_upload")
    content_kind: Mapped[str] = mapped_column(String(24), default="article_page")
    search_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovery_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    research_job_id: Mapped[int | None] = mapped_column(ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[Source] = relationship(back_populates="articles")
    analysis: Mapped[ArticleAnalysis | None] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )
    embedding: Mapped[Embedding | None] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )
    story_links: Mapped[list[StoryArticle]] = relationship(back_populates="article", cascade="all, delete-orphan")


class ArticleAnalysis(Base):
    __tablename__ = "article_analysis"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), unique=True, index=True)
    goi_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_goi_relevant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    relevance_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(20), default="uncertain", index=True)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list[dict]] = mapped_column(JSON, default=list)
    topics: Mapped[list[dict]] = mapped_column(JSON, default=list)
    entities: Mapped[list[dict]] = mapped_column(JSON, default=list)
    claims: Mapped[list[dict]] = mapped_column(JSON, default=list)
    concerns: Mapped[list[dict]] = mapped_column(JSON, default=list)
    positive_aspects: Mapped[list[dict]] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    model: Mapped[str] = mapped_column(String(120), default="local-evidence-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    article: Mapped[Article] = relationship(back_populates="analysis")


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    goi_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    is_manually_curated: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    article_links: Mapped[list[StoryArticle]] = relationship(back_populates="story", cascade="all, delete-orphan")


class StoryArticle(Base):
    __tablename__ = "story_articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__ = (UniqueConstraint("story_id", "article_id"),)
    story: Mapped[Story] = relationship(back_populates="article_links")
    article: Mapped[Article] = relationship(back_populates="story_links")


class Embedding(Base):
    __tablename__ = "embeddings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), unique=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(160))
    vector: Mapped[list[float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    article: Mapped[Article] = relationship(back_populates="embedding")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
