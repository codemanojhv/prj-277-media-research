# Delivery checklist

Progress uses ten equally weighted feature groups to make the requested 60% target auditable. Groups 1–6 form this functional milestone. A group is only marked complete after the implementation and local acceptance check pass.

| # | Capability group | Acceptance evidence | State |
|---|---|---|---|
| 1 | Local foundation, schema/migration, 100 synthetic articles, one-command demo | `npm run demo` migrated SQLite, loaded and processed 100 records into 10 stories, then passed API health and dashboard checks | Verified complete (2026-09-23) |
| 2 | Dataset/RSS/URL/online search ingestion, cleaning, duplicate handling, provenance | API tests cover JSON, CSV, mocked RSS, manual URL collection, search date/language/outlet filters, full-page capture, excerpt fallback, and job provenance | Verified complete (2026-09-23) |
| 3 | Five-language detection and GoI relevance | Unit tests cover English, Hindi, Kannada, Tamil and Telugu detection plus central-government relevance and non-relevance | Verified complete (2026-09-23) |
| 4 | Summary, sentiment, stance, topics, entities, claims, concerns, positives | Analysis tests cover separated sentiment/stance, target, confidence and evidence; browser detail shows stored evidence and provenance | Verified complete (2026-09-23) |
| 5 | Local embeddings, story clustering, shared/different coverage | Pipeline tests separate unrelated concepts; live seed has 10 clusters of 10 articles, each spanning five languages and 10 sources | Verified complete (2026-09-23) |
| 6 | REST API + dashboard → online search → story/article workflow | Search job API test verifies stored, job-scoped articles and story navigation; browser check verifies query form, progress, and result view | Verified complete (2026-09-23) |
| 7 | Expanded source/language analytics | Dedicated analytical views | Deferred |
| 8 | Global semantic search, full filter matrix, manual cluster correction | Scoped topic-driven provider search is delivered; cross-index semantic search and researcher overrides are not in this slice | Partial |
| 9 | Pipeline administration, retry controls, scheduling | Job management and operational UI | Deferred |
| 10 | Production deployment and broad release hardening | Cloudflare Workers + D1 prototype published; HTTP smoke checked dashboard, D1 metrics, story detail, article evidence, and keyless provider status | Partial: hosted university demo works; security/performance hardening and full model evaluation remain deferred |
