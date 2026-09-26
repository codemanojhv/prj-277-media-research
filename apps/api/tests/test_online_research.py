from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api import routes
from app.db.models import Article, ProcessingJob, Story, StoryArticle
from app.db.session import get_db
from app.main import app
from app.services import news_research


def test_search_candidates_respect_dates_languages_and_selected_outlets(monkeypatch):
    entries = [
        {
            "title": "Swachh Bharat public sanitation update",
            "link": "https://www.thehindu.com/news/sbm-update",
            "source": {"title": "The Hindu"},
            "published": "Sun, 20 Sep 2026 10:00:00 GMT",
            "summary": "A Government of India sanitation programme update with a local implementation report.",
        },
        {
            "title": "Old Swachh Bharat update",
            "link": "https://www.thehindu.com/news/old-sbm",
            "source": {"title": "The Hindu"},
            "published": "Sun, 01 Sep 2026 10:00:00 GMT",
            "summary": "A Government of India sanitation programme update from an earlier date.",
        },
        {
            "title": "Swachh Bharat update from another outlet",
            "link": "https://example.com/news/sbm",
            "source": {"title": "Example News"},
            "published": "Sun, 20 Sep 2026 10:00:00 GMT",
            "summary": "A Government of India sanitation programme update at a different outlet.",
        },
        {
            "title": "स्वच्छ भारत अभियान की खबर",
            "link": "https://www.thehindu.com/news/hindi-sbm",
            "source": {"title": "The Hindu"},
            "published": "Sun, 20 Sep 2026 10:00:00 GMT",
            "summary": "भारत सरकार ने स्वच्छता अभियान की नई जानकारी साझा की।",
        },
    ]
    monkeypatch.setattr(news_research, "_fetch_feed", lambda url, params: entries if "google" in url else [])

    found, provider_counts, warnings = news_research._search_candidates(
        ["Swachh Bharat"], date(2026, 9, 15), date(2026, 9, 23), ["en"], ["the-hindu"]
    )

    assert len(found) == 1
    assert found[0].title == "Swachh Bharat public sanitation update"
    assert found[0].domain == "thehindu.com"
    assert provider_counts["Google News RSS"] == 4
    assert warnings == []


def test_bing_apiclick_unwraps_publisher_article_url():
    source_url = "https://www.thehindu.com/news/national/swachh-bharat-update/article123.ece"
    wrapped = f"https://www.bing.com/news/apiclick.aspx?{urlencode({'url': source_url, 'ref': 'demo'})}"
    assert news_research._publisher_url(wrapped) == source_url


def test_online_collection_stores_capture_type_and_job_provenance(monkeypatch, db):
    published = "Sun, 20 Sep 2026 10:00:00 GMT"
    entry = {
        "title": "Swachh Bharat sanitation update",
        "link": "https://www.thehindu.com/news/sbm-update",
        "source": {"title": "The Hindu"},
        "published": published,
        "summary": "The Government of India sanitation initiative reached a new group of communities this week.",
    }
    monkeypatch.setattr(news_research, "_fetch_feed", lambda url, params: [entry] if "google" in url else [entry])
    monkeypatch.setattr(news_research, "fetch_article_record", lambda url: {
        "url": url,
        "title": "Publisher title",
        "raw_content": "<article><p>The Government of India sanitation initiative reached a new group of communities this week.</p></article>",
        "content": "The Government of India sanitation initiative reached a new group of communities this week.",
        "published_at": published,
        "source_name": "The Hindu",
        "domain": "thehindu.com",
    })
    job = ProcessingJob(job_type="online-research", status="running", metadata_json={})
    db.add(job)
    db.flush()

    result = news_research.collect_online_coverage(
        db,
        query="Swachh Bharat",
        aliases=["Clean India campaign"],
        from_date=date(2026, 9, 15),
        to_date=date(2026, 9, 23),
        languages=["en"],
        outlet_ids=["the-hindu"],
        per_language_limit=5,
        job_id=job.id,
    )

    article = db.get(Article, result["article_ids"][0])
    assert result["created"] == 1
    assert result["duplicates"] == 0
    assert result["full_text_count"] == 1
    assert result["excerpt_count"] == 0
    assert article.research_job_id == job.id
    assert article.collection_method == "online_search"
    assert article.content_kind == "article_page"
    assert article.search_query == "Swachh Bharat | Clean India campaign"
    assert article.discovery_url == entry["link"]


def test_online_collection_marks_feed_excerpt_when_publisher_page_fails(monkeypatch, db):
    entry = {
        "title": "Make in India programme coverage",
        "link": "https://www.thehindu.com/news/make-in-india",
        "source": {"title": "The Hindu"},
        "published": "Sun, 20 Sep 2026 10:00:00 GMT",
        "summary": "The Make in India programme was discussed in a new Government of India industry report.",
    }
    monkeypatch.setattr(news_research, "_fetch_feed", lambda url, params: [entry] if "google" in url else [])

    def inaccessible(_url):
        raise httpx.ConnectError("publisher page unavailable")

    monkeypatch.setattr(news_research, "fetch_article_record", inaccessible)
    job = ProcessingJob(job_type="online-research", status="running", metadata_json={})
    db.add(job)
    db.flush()

    result = news_research.collect_online_coverage(
        db,
        query="Make in India",
        aliases=[],
        from_date=date(2026, 9, 15),
        to_date=date(2026, 9, 23),
        languages=["en"],
        outlet_ids=["the-hindu"],
        per_language_limit=5,
        job_id=job.id,
    )

    article = db.get(Article, result["article_ids"][0])
    assert result["created"] == 1
    assert result["full_text_count"] == 0
    assert result["excerpt_count"] == 1
    assert article.content_kind == "feed_excerpt"
    assert "Government of India industry report" in article.clean_content


def test_research_api_search_job_stores_articles_and_scopes_story_routes(test_engine, monkeypatch):
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db():
        session = test_sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(routes, "SessionLocal", test_sessions)

    def fake_collect(db, *, job_id, query, **_kwargs):
        from app.services.ingestion import ingest_records

        records = [
            {"title": "Swachh Bharat report A", "content": "The Government of India sanitation initiative reported new community participation and expanded public cleaning work.", "url": "https://one.example.invalid/sbm", "source_name": "One Desk", "language": "en", "published_at": "2026-09-20", "collection_method": "online_search", "content_kind": "article_page", "research_job_id": job_id, "search_query": query},
            {"title": "Swachh Bharat report B", "content": "The Government of India sanitation initiative described local public cleaning work and new community participation.", "url": "https://two.example.invalid/sbm", "source_name": "Two Desk", "language": "en", "published_at": "2026-09-21", "collection_method": "online_search", "content_kind": "article_page", "research_job_id": job_id, "search_query": query},
        ]
        result = ingest_records(db, records)
        result.update({"query": query, "full_text_count": 2, "excerpt_count": 0, "warnings": [], "provider_counts": {"Google News RSS": 2, "Bing News RSS": 0}})
        return result

    def fake_process(db, *, article_ids, progress=None):
        articles = list(db.scalars(select(Article).where(Article.id.in_(article_ids))))
        story = Story(canonical_title="Swachh Bharat coverage", summary="A stored sample of initiative coverage.", first_seen=min(a.published_at for a in articles), last_updated=max(a.published_at for a in articles))
        db.add(story)
        db.flush()
        for article in articles:
            db.add(StoryArticle(story_id=story.id, article_id=article.id, similarity_score=0.8))
        if progress:
            progress(100)
        return {"articles_processed": len(articles), "stories_created": 1, "embedding_model": "test-local"}

    monkeypatch.setattr(routes, "collect_online_coverage", fake_collect)
    monkeypatch.setattr(routes, "process_corpus", fake_process)
    try:
        with TestClient(app) as client:
            options = client.get("/api/research/options")
            assert options.status_code == 200
            assert options.json()["requires_api_key"] is False
            response = client.post("/api/research/search", json={
                "query": "Swachh Bharat",
                "aliases": ["Clean India"],
                "from_date": "2026-09-01",
                "to_date": "2026-09-23",
                "languages": ["en"],
                "outlet_ids": [],
                "per_language_limit": 5,
            })
            assert response.status_code == 202
            job_id = response.json()["id"]
            job = client.get(f"/api/research/jobs/{job_id}").json()
            assert job["status"] == "completed"
            assert job["metadata"]["result"]["created"] == 2
            assert len(job["metadata"]["result"]["story_ids"]) == 1
            articles = client.get(f"/api/articles?research_job_id={job_id}").json()
            stories = client.get(f"/api/stories?research_job_id={job_id}").json()
            assert articles["count"] == 2
            assert stories["count"] == 1
            story_detail = client.get(f"/api/stories/{stories['items'][0]['id']}").json()
            assert story_detail["article_count"] == 2
            article_detail = client.get(f"/api/articles/{articles['items'][0]['id']}").json()
            assert article_detail["research_job_id"] == job_id
            assert article_detail["search_query"] == "Swachh Bharat"
    finally:
        app.dependency_overrides.clear()
