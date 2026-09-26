from __future__ import annotations

import json

import httpx
import pytest

from app.services.ingestion import ingest_records
from app.services.jev import JevDecisionProvider, JevProviderError, apply_jev_decisions


def jev_payload() -> dict:
    return {
        "model": "jev-1.13.0",
        "answers": {
            "goi_relevance": {"type": "noul", "noul": 0.87},
            "sentiment": {
                "type": "choice", "choice": "mixed", "confidence": 0.82,
                "probabilities": {"positive": 0.12, "negative": 0.11, "mixed": 0.68, "neutral": 0.06, "uncertain": 0.03},
            },
            "stance": {
                "type": "choice", "choice": "critical", "confidence": 0.78,
                "probabilities": {"supportive": 0.08, "critical": 0.78, "mixed": 0.09, "unclear": 0.05},
            },
            "primary_topic": {
                "type": "choice", "choice": "governance", "confidence": 0.75,
                "probabilities": {"governance": 0.75, "welfare": 0.15, "other": 0.1},
            },
        },
        "usage": {"input_tokens": 240, "output_tokens": 12},
    }


def test_jev_uses_one_typed_request_for_unicode_article():
    observed = {}

    def respond(request: httpx.Request) -> httpx.Response:
        observed["authorization"] = request.headers["Authorization"]
        observed["body"] = json.loads(request.content)
        return httpx.Response(200, json=jev_payload())

    provider = JevDecisionProvider(
        "test-secret", model="jev-latest", transport=httpx.MockTransport(respond), max_article_chars=500
    )
    result = provider.classify_article("भारत सरकार की नई पहल", "यह स्थानीय स्तर पर लागू कार्यक्रम की खबर है।", "hi")

    assert observed["authorization"] == "Bearer test-secret"
    assert observed["body"]["model"] == "jev-latest"
    assert observed["body"]["state"]["language"] == "hi"
    assert "भारत सरकार" in observed["body"]["state"]["article_text"]
    assert set(observed["body"]["questions"]) == {"goi_relevance", "sentiment", "stance", "primary_topic"}
    assert result["model"] == "jev-1.13.0"
    assert result["relevance"]["probability_yes"] == 0.87
    assert result["sentiment"]["choice"] == "mixed"
    assert result["usage"] == {"input_tokens": 240, "output_tokens": 12}


def test_jev_rejects_unknown_choices_and_invalid_probabilities():
    payload = jev_payload()
    payload["answers"]["sentiment"]["choice"] = "invented"
    provider = JevDecisionProvider(
        "test-secret", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    with pytest.raises(JevProviderError, match="unknown sentiment label"):
        provider.classify_article("title", "body", "en")

    payload = jev_payload()
    payload["answers"]["goi_relevance"]["noul"] = 1.2
    provider = JevDecisionProvider(
        "test-secret", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    with pytest.raises(JevProviderError, match="invalid probability"):
        provider.classify_article("title", "body", "en")


def test_jev_http_failure_does_not_include_response_body():
    provider = JevDecisionProvider(
        "test-secret",
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="private token diagnostic")),
    )
    with pytest.raises(JevProviderError, match="HTTP 401") as error:
        provider.classify_article("title", "body", "en")
    assert "private token diagnostic" not in str(error.value)


def test_jev_decisions_respect_confidence_target_and_evidence_boundaries():
    local = {
        "sentiment": "uncertain", "sentiment_score": 0.0, "sentiment_confidence": 0.25,
        "stance": "unclear", "stance_target": "Union Government policy", "stance_confidence": 0.22,
        "evidence": {"sentiment": ["The source's evidence sentence."], "stance": [], "topics": [], "summary": []},
        "model": "local-evidence-rules-v1/en",
    }
    baseline_relevance = {"score": 0.3, "is_relevant": False, "reasons": ["local indicator"]}
    decisions = {
        "provider": "TypeSafe AI JEV", "model": "jev-1.13.0", "input_characters": 83, "truncated": False,
        "usage": {"input_tokens": 20, "output_tokens": 4},
        "relevance": {"probability_yes": 0.87},
        "sentiment": {"choice": "mixed", "confidence": 0.82, "probabilities": {"positive": 0.12, "negative": 0.11, "mixed": 0.68}},
        "stance": {"choice": "critical", "confidence": 0.78, "probabilities": {"critical": 0.78}},
        "primary_topic": {"choice": "governance", "confidence": 0.75, "probabilities": {"governance": 0.75}},
    }

    enriched, relevance = apply_jev_decisions(local, baseline_relevance, decisions, 0.60)
    assert enriched["sentiment"] == "mixed"
    assert enriched["stance"] == "critical"
    assert enriched["evidence"]["sentiment"] == local["evidence"]["sentiment"]
    assert "quote-level rationales" in enriched["evidence"]["provider_decisions"]["note"]
    assert enriched["evidence"]["provider_decisions"]["primary_topic"]["used_in_topic_counts"] is False
    assert relevance["score"] == 0.87
    assert relevance["is_relevant"] is True

    decisions["sentiment"]["confidence"] = 0.4
    decisions["stance"]["confidence"] = 0.95
    local["stance_target"] = "Unspecified target"
    low_confidence, _ = apply_jev_decisions(local, baseline_relevance, decisions, 0.60)
    assert low_confidence["sentiment"] == "uncertain"
    assert low_confidence["stance"] == "unclear"
    assert low_confidence["evidence"]["provider_decisions"]["stance"]["used"] is False


def test_pipeline_sends_only_non_synthetic_articles_to_jev(monkeypatch, db):
    import app.services.pipeline as pipeline

    class FakeEmbeddingProvider:
        def __init__(self):
            pass

        def embed(self, texts: list[str]):
            return [[1.0, 0.0] for _ in texts], "test-embedding"

    class FakeJevProvider:
        def __init__(self):
            self.titles = []

        def classify_article(self, title: str, content: str, language: str):
            self.titles.append(title)
            return {
                "provider": "TypeSafe AI JEV", "model": "jev-test", "input_characters": len(content),
                "truncated": False, "usage": {"input_tokens": 15, "output_tokens": 4},
                "relevance": {"probability_yes": 0.9},
                "sentiment": {"choice": "positive", "confidence": 0.9, "probabilities": {"positive": 0.9, "negative": 0.02}},
                "stance": {"choice": "supportive", "confidence": 0.85, "probabilities": {"supportive": 0.85}},
                "primary_topic": {"choice": "welfare", "confidence": 0.8, "probabilities": {"welfare": 0.8}},
            }

    jev = FakeJevProvider()
    monkeypatch.setattr(pipeline, "EmbeddingProvider", FakeEmbeddingProvider)
    monkeypatch.setattr(pipeline.jev_service.config, "ANALYSIS_PROVIDER", "typesafe")
    monkeypatch.setattr(pipeline.jev_service, "configured_jev_provider", lambda: jev)
    ingest_records(db, [
        {
            "title": "Collected policy article",
            "content": "The Government of India announced a welfare programme and described its planned benefits.",
            "url": "https://publisher.example.invalid/collected-policy",
            "source_name": "Collected Desk", "language": "en", "published_at": "2026-09-20",
        },
        {
            "title": "Synthetic classroom article",
            "content": "Synthetic sample. The Government of India described a fictional welfare programme.",
            "url": "synthetic://classroom/policy", "source_name": "Synthetic Desk",
            "language": "en", "is_synthetic": True, "published_at": "2026-09-20",
        },
    ])

    result = pipeline.process_corpus(db)
    articles = list(db.query(pipeline.Article).order_by(pipeline.Article.id))
    assert result["articles_processed"] == 2
    assert jev.titles == ["Collected policy article"]
    assert "typesafe-ai/jev-test" in articles[0].analysis.model
    assert articles[0].analysis.evidence["provider_decisions"]["model"] == "jev-test"
    assert articles[1].analysis.model.startswith("local-evidence-rules-v1")
