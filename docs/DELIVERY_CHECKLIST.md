# Delivery checklist

Progress uses ten equally weighted capability groups. Groups 1–9 now have local implementations; group 10 remains an external evidence and release gate. This is feature-scope accounting, not a production-readiness score.

| # | Capability group | Acceptance evidence | State |
|---|---|---|---|
| 1 | Local foundation, schema/migration, 100 synthetic articles, one-command demo | `npm run demo` migrated SQLite, loaded and processed 100 records into 10 stories, then passed API health and dashboard checks | Verified complete (2026-09-23) |
| 2 | Dataset/RSS/URL/online search ingestion, cleaning, duplicate handling, provenance | API tests cover JSON, CSV, mocked RSS, manual URL collection, search date/language/outlet filters, full-page capture, excerpt fallback, and job provenance | Verified complete (2026-09-23) |
| 3 | Five-language detection and GoI relevance | Unit tests cover English, Hindi, Kannada, Tamil and Telugu detection plus central-government relevance and non-relevance | Verified complete (2026-09-23) |
| 4 | Evidence-linked summary, article tone, topics, entities, claims, concerns, positives, and public-reaction view | Article detail separates article tone from matched Bluesky/Hacker News reactions; neutral/uncertain reactions do not affect direction | Verified complete (2026-10-23) |
| 5 | Local embeddings, story clustering, shared/different coverage | Pipeline tests separate unrelated concepts; live seed has 10 clusters of 10 articles, each spanning five languages and 10 sources | Verified complete (2026-09-23) |
| 6 | REST API + dashboard → online search → story/article workflow | Search job API test verifies stored, job-scoped articles and story navigation; browser check verifies query form, progress, and result view | Verified complete (2026-09-23) |
| 7 | Expanded source/language analytics | Dedicated source and language breakdowns with date and corpus filters; also supported by the D1 adapter | Implemented; build checked |
| 8 | Global search, full filter matrix, manual cluster correction | Local saved-embedding search, article filters, title/summary edits, membership changes, and merge persistence; D1 falls back to keyword ranking | Implemented locally; hosted manual edits are disabled pending write protection |
| 9 | Pipeline administration, retry controls, scheduling | Local source registry, feed collection, recurring schedule, job retry, and full reanalysis controls | Implemented locally; lint/build checked |
| 10 | Production deployment, security/performance hardening, and full model evaluation | Cloudflare Worker version `8b2b028f-c3ae-4786-a7cd-fa316b1910f6` deployed (2026-10-23); human-labeled representative corpus and security/performance review remain | Pending external evaluation and hardening |

Current local feature-scope score: **90% (9/10 groups)**. The remaining 10% cannot be evidenced by synthetic data or local compilation alone.
