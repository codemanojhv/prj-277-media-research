from __future__ import annotations

import json
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Article
from app.db.session import get_db
from app.main import app
from app.services.ingestion import ingest_records


@pytest.fixture
def client(test_engine) -> Generator[TestClient, None, None]:
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db():
        session: Session = test_sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_dataset_upload_persists_articles_and_database_metrics(client):
    records = [{
        "title": "Synthetic Government of India health demo",
        "content": "This fictional sample describes a Government of India public health clinic service. It is not real reporting.",
        "url": "synthetic://test/health",
        "source_name": "Synthetic English Desk",
        "language": "en",
        "is_synthetic": True,
    }]
    response = client.post("/api/ingestion/dataset", files={"file": ("sample.json", json.dumps({"articles": records}), "application/json")})
    assert response.status_code == 200
    assert response.json()["created"] == 1
    overview = client.get("/api/analytics/overview").json()
    assert overview["total_articles"] == 1
    assert overview["synthetic_articles"] == 1
    article = client.get("/api/articles/1").json()
    assert article["url"] == "synthetic://test/health"
    assert article["content_hash"]
    assert article["raw_content"]


def test_csv_upload_preserves_unicode_content(client):
    csv_data = (
        'title,content,url,source_name,language\n'
        'भारत सरकार की नमूना खबर,"यह Unicode नमूना लेख सार्वजनिक सेवा के बारे में है।",'
        'synthetic://csv/health,Synthetic Hindi Desk,hi\n'
    )
    response = client.post(
        "/api/ingestion/dataset",
        files={"file": ("sample.csv", csv_data.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1
    article = client.get("/api/articles/1").json()
    assert article["language"] == "hi"
    assert "सार्वजनिक सेवा" in article["content"]


def test_rss_and_manual_url_ingestion_paths(client, monkeypatch):
    from app.services import ingestion

    feed_url = "https://feed.example.invalid/demo.xml"
    article_url = "https://news.example.invalid/rss-story"
    manual_url = "https://news.example.invalid/manual-story"
    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Synthetic Feed Desk</title>
    <item><title>Fictional public service</title><link>{article_url}</link>
    <description>A fictional Government of India public service sample for research.</description>
    <pubDate>Wed, 23 Sep 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    article_html = """<html><head><title>Fallback page title</title></head><body>
    <article><h1>Fictional service article</h1>
    <p>Synthetic research sample. The Government of India shared a public clinic service demonstration.</p>
    </article></body></html>"""

    def response(url: str, body: str, content_type: str) -> httpx.Response:
        return httpx.Response(
            200,
            content=body.encode("utf-8"),
            headers={"content-type": content_type},
            request=httpx.Request("GET", url),
        )

    def fake_get_public_url(url: str) -> httpx.Response:
        if url == feed_url:
            return response(url, feed_xml, "application/rss+xml")
        if url == manual_url:
            unique_article = article_html.replace("public clinic service", "rural water service")
            return response(url, unique_article, "text/html; charset=utf-8")
        return response(url, article_html, "text/html; charset=utf-8")

    monkeypatch.setattr(ingestion, "_get_public_url", fake_get_public_url)
    rss_result = client.post("/api/ingestion/rss", json={"url": feed_url, "max_entries": 1})
    assert rss_result.status_code == 200
    assert rss_result.json()["created"] == 1
    rss_article = client.get("/api/articles/1").json()
    assert rss_article["source"]["name"] == "Synthetic Feed Desk"
    assert "public clinic service" in rss_article["content"]

    url_result = client.post("/api/ingestion/url", json={"url": manual_url})
    assert url_result.status_code == 200
    assert url_result.json()["created"] == 1
    manual_article = client.get("/api/articles/2").json()
    assert manual_article["url"] == manual_url
    assert manual_article["raw_content"].startswith("<html>")


def test_story_route_exposes_language_and_source_comparison(client, test_engine, monkeypatch):
    from app.services import pipeline

    class FixedProvider:
        def __init__(self, model_name=None):
            pass

        def embed(self, texts):
            from app.services.embeddings import matched_concepts

            return [[1.0, 0.0] if "solar-energy" in matched_concepts(text) else [0.0, 1.0] for text in texts], "test-api-embedding"

    monkeypatch.setattr(pipeline, "EmbeddingProvider", FixedProvider)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    with test_sessions() as db:
        records = [
            {"title": "Solar service briefing", "content": "Synthetic note. Government of India shared a solar rooftop service. Supporters welcomed improvement and benefit.", "url": "synthetic://api/solar/en", "source_name": "English Desk", "language": "en", "is_synthetic": True},
            {"title": "सौर सेवा विवरण", "content": "काल्पनिक नमूना। भारत सरकार ने सौर सेवा साझा की। समर्थकों ने सुधार और लाभ का स्वागत किया।", "url": "synthetic://api/solar/hi", "source_name": "Hindi Desk", "language": "hi", "is_synthetic": True},
        ]
        ingest_records(db, records)
        pipeline.process_corpus(db)
        article_id = db.query(Article.id).order_by(Article.id).first()[0]
    stories = client.get("/api/stories").json()["items"]
    assert len(stories) == 1
    detail = client.get(f"/api/stories/{stories[0]['id']}").json()
    assert detail["article_count"] == 2
    assert {item["language"] for item in detail["comparison"]["language_comparison"]} == {"en", "hi"}
    assert len(detail["comparison"]["source_comparison"]) == 2
    article = client.get(f"/api/articles/{article_id}").json()
    assert article["analysis"]["evidence"]["summary"]
    assert article["story"]["id"] == stories[0]["id"]


def test_pipeline_job_endpoint_reports_completion(client, test_engine, monkeypatch):
    from app.api import routes

    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(routes, "SessionLocal", test_sessions)

    def fake_pipeline(db, progress=None):
        if progress:
            progress(70)
        return {"articles_processed": 2, "stories_created": 1, "embedding_model": "test-v1"}

    monkeypatch.setattr(routes, "process_corpus", fake_pipeline)
    response = client.post("/api/pipeline/run")
    assert response.status_code == 202
    job_id = response.json()["id"]
    status = client.get(f"/api/pipeline/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert status["progress"] == 100
    assert status["metadata"]["stories_created"] == 1
