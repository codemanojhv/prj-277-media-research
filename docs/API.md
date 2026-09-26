# API quick reference

FastAPI's interactive OpenAPI page is available at `http://127.0.0.1:8000/docs` during the demo.

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/analytics/overview` | Stored dataset metrics and distributions |
| GET | `/api/stories` | Story clusters with language/source/date/region filters |
| GET | `/api/stories/{id}` | Story articles plus language/source comparison and evidence references |
| GET | `/api/articles` | Article list with language/source/date/region/story filters |
| GET | `/api/articles/{id}` | Raw/clean text, provenance, and analysis evidence |
| GET | `/api/articles/{id}/reactions` | Latest public-post sentiment sample and source links |
| POST | `/api/articles/{id}/reactions/collect` | Search public Bluesky posts and Hacker News comments, classify with JEV, summarize with Gemini, and persist provenance |
| GET | `/api/sources`, `/api/languages`, `/api/topics` | Database-backed filter options and counts |
| GET | `/api/research/options` | Supported language/outlet choices, date defaults, and provider/API-key information |
| POST | `/api/research/search` | Start a topic-driven online news collection, analysis, and clustering job |
| GET | `/api/research/jobs`, `/api/research/jobs/{id}` | List search runs and read request, progress, results, and collection notes |
| POST | `/api/ingestion/dataset` | Multipart JSON/CSV upload, max 5 MB |
| POST | `/api/ingestion/url` | Collect one public article URL |
| POST | `/api/ingestion/rss` | Collect up to the requested number of public RSS entries |
| POST | `/api/pipeline/run` | Start an asynchronous local process/cluster job |
| GET | `/api/pipeline/jobs`, `/api/pipeline/jobs/{id}` | Read processing job status and output |

The online research request accepts `query`, optional `aliases`, `from_date`, `to_date`, `languages`, optional `outlet_ids`, and `per_language_limit` (1–10). The maximum date span is 366 days. Use `research_job_id` on article and story list endpoints to scope the result to that job. A search job never rebuilds or reclusters the synthetic demo corpus.

Public reaction search is available only for non-synthetic article records. It collects up to 12 Bluesky posts and Hacker News comments matched by the source URL or a strong headline/thread-title match. Original permalinks and exact text are retained, and each item counts once. A per-article five-minute cache avoids repeated provider calls. JEV classifies each item separately; Gemini can write a sample-level summary linked to collected text. If analysis providers are unavailable, records remain unlabeled as `uncertain` and the API says analysis was unavailable. News coverage feeds do not contain audience reactions; publisher comment sections and social networks require separate source-specific integrations.
