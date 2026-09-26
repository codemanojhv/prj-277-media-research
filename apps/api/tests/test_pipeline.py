from __future__ import annotations

from sqlalchemy import select

from app.db.models import Article, ProcessingJob, Story, StoryArticle
from app.seed import generate_demo_articles
from app.services.analysis import analyze_article
from app.services.embeddings import matched_concepts
from app.services.ingestion import ingest_records, normalize_record
from app.services.language import detect_language
from app.services.pipeline import process_corpus
from app.services.relevance import assess_relevance


class FakeEmbeddingProvider:
    def __init__(self, model_name: str | None = None):
        pass

    def embed(self, texts: list[str]):
        concepts = ["solar-energy", "rural-water", "digital-learning", "public-health", "farm-services", "road-safety", "clean-cooking", "public-digital-services", "skills-employment", "public-budget"]
        vectors = []
        for text in texts:
            found = set(matched_concepts(text))
            vectors.append([1.0 if concept in found else 0.0 for concept in concepts])
        return vectors, "test-embedding-v1"


def test_detects_five_supported_languages():
    fixtures = {
        "en": "The Government of India shared a public service note.",
        "hi": "भारत सरकार ने सार्वजनिक सेवा के बारे में जानकारी साझा की।",
        "kn": "ಭಾರತ ಸರ್ಕಾರ ಸಾರ್ವಜನಿಕ ಸೇವೆಯ ಬಗ್ಗೆ ಮಾಹಿತಿಯನ್ನು ಹಂಚಿಕೊಂಡಿತು.",
        "ta": "இந்திய அரசு பொது சேவை குறித்த தகவலைப் பகிர்ந்தது.",
        "te": "భారత ప్రభుత్వం ప్రజా సేవ గురించి సమాచారాన్ని పంచుకుంది.",
    }
    for expected, text in fixtures.items():
        language, confidence = detect_language(text)
        assert language == expected
        assert 0.5 <= confidence <= 1.0


def test_normalizes_unicode_html_and_duplicate_content(db):
    record = {
        "title": "भारत सरकार की नमूना खबर",
        "content": "<article><nav>Ignore menu</nav><p>यह Unicode नमूना लेख पर्याप्त लंबा है और इसमें सार्वजनिक सेवा की जानकारी दी गई है।</p><script>ignore();</script></article>",
        "url": "https://publisher.example.invalid/story-1",
        "source_name": "Test Regional Desk",
        "published_at": "2026-09-20T10:00:00Z",
    }
    normalized = normalize_record(record)
    assert "Ignore menu" not in normalized["clean_content"]
    assert "Unicode" in normalized["clean_content"]
    assert normalized["language"] == "hi"
    first = ingest_records(db, [record])
    second = ingest_records(db, [record])
    assert first["created"] == 1
    assert second["duplicates"] == 1
    assert second["created"] == 0


def test_relevance_requires_central_government_evidence():
    assert assess_relevance("The Government of India published a central scheme.")["is_relevant"]
    assert assess_relevance("Swachh Bharat Mission's next phase focuses on sanitation.")["is_relevant"]
    assert assess_relevance("Make in India supports manufacturing and local industry.")["is_relevant"]
    assert assess_relevance("स्वच्छ भारत मिशन का अगला चरण जारी है।")["is_relevant"]
    result = assess_relevance("A politician spoke at a local rally. No central policy was discussed.")
    assert not result["is_relevant"]
    assert result["reasons"] == []


def test_analysis_keeps_sentiment_and_stance_separate_and_evidence_linked():
    result = analyze_article(
        "The Government of India announced a welfare scheme. Supporters welcomed the improvement and described a benefit. Local groups raised concerns about delay and limited access.",
        "en",
    )
    assert result["sentiment"] == "mixed"
    assert result["stance"] == "mixed"
    assert result["stance_target"] == "Union Government policy"
    assert result["evidence"]["sentiment"]
    assert result["concerns"]
    assert result["positive_aspects"]
    assert all("confidence" in point for point in result["topics"])


def test_local_pipeline_clusters_related_multilingual_articles(monkeypatch, db):
    import app.services.pipeline as pipeline

    monkeypatch.setattr(pipeline, "EmbeddingProvider", FakeEmbeddingProvider)
    records = [
        {"title": "Fictional solar service briefing", "content": "Synthetic exercise. Government of India shared solar rooftop access. Supporters welcomed improvement and benefit for households.", "url": "https://one.example.invalid/solar", "source_name": "One Desk", "language": "en", "published_at": "2026-09-20"},
        {"title": "काल्पनिक सौर सेवा", "content": "यह काल्पनिक नमूना है। भारत सरकार ने सौर सेवा साझा की। समर्थकों ने सुधार और लाभ का स्वागत किया।", "url": "https://two.example.invalid/solar", "source_name": "Two Desk", "language": "hi", "published_at": "2026-09-20"},
        {"title": "Fictional rural water note", "content": "Synthetic exercise. Government of India shared rural water access. Readers raised concerns about delay and limited access.", "url": "https://three.example.invalid/water", "source_name": "Three Desk", "language": "en", "published_at": "2026-09-20"},
    ]
    assert ingest_records(db, records)["created"] == 3
    result = process_corpus(db)
    assert result["articles_processed"] == 3
    assert result["stories_created"] == 2
    assert len(list(db.scalars(select(Story)))) == 2
    articles = list(db.scalars(select(Article).order_by(Article.id)))
    assert articles[0].analysis is not None
    assert articles[0].analysis.evidence["sentiment"]
    solar_story_ids = {link.story_id for article in articles[:2] for link in article.story_links}
    water_story_ids = {link.story_id for link in articles[2].story_links}
    assert len(solar_story_ids) == 1
    assert solar_story_ids.isdisjoint(water_story_ids)


def test_scoped_research_processing_preserves_existing_story_clusters(monkeypatch, db):
    import app.services.pipeline as pipeline

    monkeypatch.setattr(pipeline, "EmbeddingProvider", FakeEmbeddingProvider)
    initial = [
        {"title": "Synthetic solar briefing", "content": "Government of India solar-energy rooftop service reached more households. Supporters welcomed the public benefit.", "url": "synthetic://scope/solar", "source_name": "Demo Solar Desk", "language": "en", "is_synthetic": True, "published_at": "2026-09-20"},
        {"title": "Synthetic rural water briefing", "content": "Government of India rural-water services reached more villages. Residents raised concerns about delivery delays.", "url": "synthetic://scope/water", "source_name": "Demo Water Desk", "language": "en", "is_synthetic": True, "published_at": "2026-09-20"},
    ]
    assert ingest_records(db, initial)["created"] == 2
    process_corpus(db)
    original_stories = set(db.scalars(select(Story.id)))
    original_links = {(link.story_id, link.article_id) for link in db.scalars(select(StoryArticle))}

    job = ProcessingJob(job_type="online-research", status="running", metadata_json={})
    db.add(job)
    db.flush()
    collected = ingest_records(db, [
        {"title": "Online clean-cooking update", "content": "Government of India clean-cooking support reached more households. The public service adds new access and local delivery details.", "url": "https://news.example.invalid/clean-cooking", "source_name": "Online Desk", "language": "en", "published_at": "2026-09-21", "research_job_id": job.id, "collection_method": "online_search"},
    ])
    result = process_corpus(db, article_ids=collected["article_ids"])

    assert result["articles_processed"] == 1
    assert original_stories.issubset(set(db.scalars(select(Story.id))))
    assert original_links.issubset({(link.story_id, link.article_id) for link in db.scalars(select(StoryArticle))})
    assert db.scalar(select(Article).where(Article.id == collected["article_ids"][0])).analysis is not None


def test_demo_corpus_has_100_articles_and_ten_multilingual_clusters(monkeypatch, db):
    import app.services.pipeline as pipeline

    monkeypatch.setattr(pipeline, "EmbeddingProvider", FakeEmbeddingProvider)
    records = generate_demo_articles()
    assert len(records) == 100
    ingest_result = ingest_records(db, records)
    assert ingest_result["created"] == 100
    result = process_corpus(db)
    assert result["stories_created"] == 10
    memberships = list(db.scalars(select(StoryArticle)))
    by_story: dict[int, list[int]] = {}
    for membership in memberships:
        by_story.setdefault(membership.story_id, []).append(membership.article_id)
    assert sorted(len(article_ids) for article_ids in by_story.values()) == [10] * 10


def test_public_url_validation_rejects_loopback():
    from app.services.ingestion import validate_public_url

    try:
        validate_public_url("http://127.0.0.1:8000/admin")
    except ValueError as exc:
        assert "private" in str(exc) or "Local" in str(exc)
    else:
        raise AssertionError("loopback URL should be rejected")
