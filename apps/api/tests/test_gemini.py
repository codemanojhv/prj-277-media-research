from __future__ import annotations

import json

import httpx
import pytest

from app.services.gemini import GeminiProviderError, GeminiSummaryProvider, apply_gemini_summary
from app.services.ingestion import ingest_records


def gemini_response(evidence_id: int = 0) -> dict:
    return {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps({
                "summary": "The report describes an update to a public campaign and its implementation.",
                "key_points": [
                    {"text": "The article reports a campaign expansion.", "evidence_id": evidence_id},
                    {"text": "An unsupported detail.", "evidence_id": 99},
                ],
            }, ensure_ascii=False)}]}
        }]
    }


def test_gemini_uses_server_header_and_maps_unicode_sentence_ids_to_exact_evidence():
    observed = {}
    source = "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया। अधिकारियों ने इसे राज्य स्तर पर लागू किया।"

    def respond(request: httpx.Request) -> httpx.Response:
        observed["key_header"] = request.headers["x-goog-api-key"]
        observed["url"] = str(request.url)
        observed["body"] = json.loads(request.content)
        return httpx.Response(200, json=gemini_response())

    provider = GeminiSummaryProvider("test-secret", transport=httpx.MockTransport(respond))
    generated = provider.generate_summary("स्वच्छ भारत", source, "hi")

    assert observed["key_header"] == "test-secret"
    assert "?key=" not in observed["url"]
    assert "test-secret" not in observed["url"]
    assert observed["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "स्वच्छ भारत" in observed["body"]["contents"][0]["parts"][0]["text"]
    assert "[0] भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।" in observed["body"]["contents"][0]["parts"][0]["text"]
    assert len(generated["key_points"]) == 1
    assert generated["key_points"][0]["evidence"] == "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।"
    assert generated["truncated"] is False


def test_gemini_rejects_output_with_only_invalid_sentence_ids():
    provider = GeminiSummaryProvider(
        "test-secret",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=gemini_response(99))),
    )
    with pytest.raises(GeminiProviderError, match="valid source sentence IDs"):
        provider.generate_summary("स्वच्छ भारत", "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।", "hi")


def test_gemini_retries_transient_service_unavailable(monkeypatch):
    attempts = 0
    monkeypatch.setattr("app.services.gemini.time.sleep", lambda _seconds: None)

    def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="temporarily unavailable")
        return httpx.Response(200, json=gemini_response())

    provider = GeminiSummaryProvider("test-secret", transport=httpx.MockTransport(respond))
    generated = provider.generate_summary("स्वच्छ भारत", "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।", "hi")

    assert attempts == 2
    assert generated["key_points"][0]["evidence"] == "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।"


def test_gemini_uses_stable_fallback_model_after_repeated_503(monkeypatch):
    requested_models = []
    monkeypatch.setattr("app.services.gemini.time.sleep", lambda _seconds: None)

    def respond(request: httpx.Request) -> httpx.Response:
        requested_models.append(request.url.path)
        if "gemini-3.8-flash" in request.url.path:
            return httpx.Response(503, text="temporarily unavailable")
        return httpx.Response(200, json=gemini_response())

    provider = GeminiSummaryProvider("test-secret", transport=httpx.MockTransport(respond))
    generated = provider.generate_summary("स्वच्छ भारत", "भारत सरकार ने स्वच्छ भारत अभियान का विस्तार किया।", "hi")

    assert generated["model"] == "gemini-3.7-flash"
    assert any("gemini-3.8-flash" in path for path in requested_models)
    assert requested_models[-1].endswith("/models/gemini-3.7-flash:generateContent")


def test_gemini_http_errors_do_not_expose_response_body():
    provider = GeminiSummaryProvider(
        "test-secret",
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="private error and key data")),
    )
    with pytest.raises(GeminiProviderError, match="HTTP 401") as error:
        provider.generate_summary("title", "article content is sufficiently long for analysis", "en")
    assert "private error" not in str(error.value)


def test_gemini_summary_metadata_preserves_other_analysis_fields():
    local = {
        "sentiment": "uncertain",
        "model": "local-evidence-rules-v1/en",
        "evidence": {"sentiment": [], "summary": ["Local extract."]},
    }
    generated = {
        "provider": "Google Gemini",
        "model": "gemini-3.8-flash",
        "input_characters": 180,
        "truncated": False,
        "summary": "A neutral generated summary grounded in the supplied article.",
        "key_points": [{"text": "One grounded point.", "evidence": "Exact article evidence sentence."}],
    }

    result = apply_gemini_summary(local, generated)

    assert result["sentiment"] == "uncertain"
    assert result["summary"] == generated["summary"]
    assert result["evidence"]["summary"] == ["Exact article evidence sentence."]
    assert result["evidence"]["gemini_generation"]["key_points"] == generated["key_points"]
    assert "+gemini/gemini-3.8-flash" in result["model"]
    assert "not verified facts" in result["evidence"]["gemini_generation"]["note"]


def test_provider_status_shows_gemini_independently_from_jev(monkeypatch):
    from app.core import config
    from app.services.jev import provider_status

    monkeypatch.setattr(config, "ANALYSIS_PROVIDER", "local")
    monkeypatch.setattr(config, "TYPESAFE_API_KEY", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

    status = provider_status()

    assert status["provider"] == "local"
    assert status["ready"] is True
    assert status["text_generation"]["provider"] == "gemini"
    assert status["text_generation"]["ready"] is True


def test_pipeline_sends_only_real_articles_to_gemini(monkeypatch, db):
    import app.services.pipeline as pipeline

    class FakeEmbeddingProvider:
        def embed(self, texts: list[str]):
            return [[1.0, 0.0] for _ in texts], "test-embedding"

    class FakeGeminiProvider:
        def __init__(self):
            self.titles = []

        def generate_summary(self, title: str, content: str, language: str):
            self.titles.append(title)
            quote = content.split(".")[0] + "."
            return {
                "provider": "Google Gemini", "model": "gemini-test", "input_characters": len(content), "truncated": False,
                "summary": "A neutral model-generated summary grounded in the collected article.",
                "key_points": [{"text": "The article reports a program update.", "evidence": quote}],
            }

    provider = FakeGeminiProvider()
    monkeypatch.setattr(pipeline, "EmbeddingProvider", FakeEmbeddingProvider)
    monkeypatch.setattr(pipeline.jev_service.config, "ANALYSIS_PROVIDER", "local")
    monkeypatch.setattr(pipeline.gemini_service.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(pipeline.gemini_service, "configured_gemini_provider", lambda: provider)
    ingest_records(db, [
        {
            "title": "Collected policy article",
            "content": "The Government of India announced a welfare programme and described its planned benefits.",
            "url": "https://publisher.example.invalid/collected-policy-gemini",
            "source_name": "Collected Desk", "language": "en", "published_at": "2026-09-20",
        },
        {
            "title": "Synthetic classroom article",
            "content": "Synthetic sample. The Government of India described a fictional welfare programme.",
            "url": "synthetic://classroom/policy-gemini", "source_name": "Synthetic Desk",
            "language": "en", "is_synthetic": True, "published_at": "2026-09-20",
        },
    ])

    result = pipeline.process_corpus(db)
    articles = list(db.query(pipeline.Article).order_by(pipeline.Article.id))

    assert result["articles_processed"] == 2
    assert provider.titles == ["Collected policy article"]
    assert articles[0].analysis.evidence["gemini_generation"]["model"] == "gemini-test"
    assert articles[0].analysis.evidence["summary"][0] in articles[0].clean_content
    assert "gemini_generation" not in articles[1].analysis.evidence
