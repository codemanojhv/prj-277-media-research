# PRJ_277 — 360-Degree Regional News Coverage Research

A local-first academic prototype for comparing how Government of India-related stories appear across regional language media. The app connects every cluster comparison to its stored article records and source provenance.

## Run the demo

Prerequisites: Python 3.12, Node.js with npm, and `uv`. No Docker daemon, paid AI key, or external database is required.

```powershell
npm run demo
```

The first run installs dependencies, applies SQLite migrations, generates and loads 100 synthetic articles in English, Hindi, Kannada, Tamil, and Telugu, runs local analysis and story clustering, then starts the API and dashboard. The multilingual embedding model is cached locally; if it cannot be downloaded or loaded, the pipeline logs a clearly labeled lexical fallback. Open the dashboard at `http://127.0.0.1:3000`, or the FastAPI docs at `http://127.0.0.1:8000/docs`. Press Ctrl+C to stop both processes.

To collect current public news coverage, open **Search coverage** or click **Search news coverage** on the dashboard. Enter a topic such as `Swachh Bharat Mission`, optional alternate names, a publication date range, and one or more languages. Optionally narrow the source sample to selected outlets. The search uses Google News RSS and Bing News RSS; no Gemini, OpenRouter, or other model API key is required. Collected records are labeled as full publisher page text or a feed excerpt and stored locally with the query and source/discovery URLs.

## Cloudflare Workers demo

The hosted student demo uses Next.js through OpenNext on Cloudflare Workers and D1 for persistent records. To publish your own copy, authenticate Wrangler with a Cloudflare account that can create Workers and D1 databases:

```powershell
cd apps/web
npx wrangler d1 create prj-277-media-research --location apac
```

Copy the returned database ID into `apps/web/wrangler.jsonc`, then from the project root run:

```powershell
npm run cf:deploy
```

The deployment command applies D1 migrations, bundles the web/API Worker, and uploads it to Cloudflare. It does not start a local server, run the Python seed pipeline, or download model weights. Collected real articles are processed through the configured JEV and Gemini APIs; provider secrets remain in Cloudflare. The deployed app does not need Docker or a custom domain. Search results are kept in a query-scoped comparison group; the hosted Worker does not use the local FastEmbed model.

### Public reaction sentiment

Open any collected real article and choose **Search public reactions**. The hosted Worker searches public Bluesky posts and Hacker News comments for the article URL or a strong headline match. Matching posts/comments are classified with TypeSafe JEV; Gemini can add a cautious sample summary linked to the collected text. Every result links to its original post/comment. Article tone and public reaction sentiment are separate. Scans are capped at 12 posts and cached for five minutes.

This is a sample of indexed public posts, not a poll or a measure of the public as a whole. A headline match may discuss the same issue rather than reply to that exact article. News coverage feeds contain publisher reporting, not reader reactions. Public comments on publisher sites use different systems and access rules; they need source-specific integrations and cannot be assumed to exist on every article.

To enable TypeSafe JEV structured decisions on your own hosted copy, run this from `apps/web` and enter the key into Wrangler's hidden prompt:

```powershell
npx wrangler secret put TYPESAFE_API_KEY
```

The secret stays server-side. JEV is used for collected non-synthetic records; synthetic examples do not call external model APIs. JEV needs a TypeSafe key specifically—Gemini and OpenRouter keys cannot authenticate to TypeSafe.

To enable Gemini summaries and key points on the hosted Worker, run this from `apps/web` and enter the key into Wrangler's hidden prompt:

```powershell
npx wrangler secret put GEMINI_API_KEY
```

Gemini and JEV are separate providers. Gemini generates article-grounded prose; evidence is selected by sentence ID and attached from the stored source text. Synthetic records do not call external model APIs. If Gemini is unavailable, the app records that provider status and uses deterministic evidence rules; no local model is downloaded. See [Cloudflare deployment and provider setup](docs/CLOUDFLARE_DEPLOYMENT.md).

## Optional TypeSafe JEV analysis

The no-key local analysis remains the default. To use TypeSafe JEV for structured Government of India relevance, sentiment, stance, and primary-topic decisions on collected non-synthetic articles, create a root `.env` from `.env.example`, set `ANALYSIS_PROVIDER=typesafe`, and add your TypeSafe API key as `TYPESAFE_API_KEY`. The API sends the key as a Bearer credential from the API server only. Gemini and OpenRouter keys do not authenticate to TypeSafe's endpoint. See the [TypeSafe API reference](https://api.typesafe.ai/docs) for account access and available model aliases.

For the local FastAPI demo, create a root `.env` from `.env.example`. Set `ANALYSIS_PROVIDER=typesafe` and `TYPESAFE_API_KEY` for JEV, and set `GEMINI_API_KEY` independently for Gemini summaries. Both can be enabled together. Restart `npm run demo`, then start a new online research search or run the pipeline to reprocess stored real articles. The 100 fictional demo records always stay local. The dashboard reports provider readiness. Bounded excerpts of collected real articles are sent only to providers whose keys are configured; JEV returns structured decisions while Gemini writes summaries and key points with exact-quote checks. Tune `JEV_MIN_CONFIDENCE`, `GEMINI_MAX_ARTICLE_CHARS`, and `GOI_RELEVANCE_THRESHOLD` in `.env` as needed.

Every demo article and source is fictional and labeled synthetic. Demo URLs use a reserved `synthetic://` scheme and do not point to real news pages.

## Project structure

```text
apps/api/       FastAPI, SQLAlchemy models, ingestion and local analysis services
apps/web/       Next.js research dashboard
data/sample/    Synthetic dataset notes
scripts/        One-command demo launcher
docs/           Architecture, methodology, data schema, limitations, and delivery checklist
```

## 60% milestone tracking

The brief is tracked as ten equally weighted capability groups. Groups 1–6 are the delivered milestone; each is marked complete only after its behavior works in the local demo.

Groups 1–6 were verified locally on 2026-09-23. The API suite covers the local demo and online search workflow; the frontend type check and production build are checked for this delivery. The online topic search is a scoped discovery workflow and does not complete global semantic search or the broader administration features below.

| # | Capability group | Milestone |
|---|---|---|
| 1 | Local foundation, SQLite, migrations, synthetic dataset, one-command demo | Complete |
| 2 | Dataset/RSS/URL ingestion, normalization, cleaning, deduplication, provenance | Complete |
| 3 | Five-language detection and configurable Government of India relevance | Complete |
| 4 | Evidence-linked summary, sentiment, stance, topics, entities, claims, concerns, positive aspects | Complete |
| 5 | Local multilingual embeddings, story clustering, neutral comparison | Complete |
| 6 | Database-backed API and dashboard → search → story comparison → article evidence flow | Complete |
| 7 | Expanded source/language analytics pages | Deferred |
| 8 | Global semantic search, full filter matrix, manual cluster correction | Partial: topic-driven news-provider search is implemented; global semantic search and full filters remain deferred |
| 9 | Pipeline administration, scheduling, retries, and source management | Deferred |
| 10 | Production deployment, broad performance/security hardening, and full model evaluation | Deferred |

This is a feature-scope accounting method, not a claim of 60% production readiness or a university rubric score.

## API

FastAPI generates interactive OpenAPI documentation at `/docs`. The main routes include:

- `GET /api/analytics/overview`, `/api/stories`, `/api/stories/{id}`, `/api/articles`, `/api/articles/{id}`
- `GET /api/sources`, `/api/languages`, `/api/topics`
- `POST /api/ingestion/dataset`, `/api/ingestion/rss`, `/api/ingestion/url`
- `GET /api/research/options`, `POST /api/research/search`, `GET /api/research/jobs`, `GET /api/research/jobs/{id}`
- `POST /api/pipeline/run`, `GET /api/pipeline/jobs`

Pass `research_job_id` to `/api/articles` or `/api/stories` to view one online search's stored sample. Overall dashboard metrics include all stored records, including clearly labeled synthetic demo records.

Dataset uploads accept UTF-8 JSON (`[{...}]` or `{"articles": [...]}`) and CSV with article columns such as `title`, `content`, `url`, `source_name`, `published_at`, `language`, and `region`. Each malformed row is reported without aborting the rest of an import.

## Local checks

```powershell
npm run test:api
npm run lint:web
npm run build:web
```

See [Methodology](docs/METHODOLOGY.md), [Architecture](docs/ARCHITECTURE.md), [Cloudflare deployment notes](docs/CLOUDFLARE_DEPLOYMENT.md), [Data schema](docs/DATA_SCHEMA.md), [Limitations](docs/LIMITATIONS.md), and the [delivery checklist](docs/DELIVERY_CHECKLIST.md).

## Hosted demo and review deck

- Live Cloudflare Workers demo: https://prj-277-media-research.manojhv13.workers.dev/
- Review-2 presentation, based on the provided university template: [docs/PRJ_277_Review2_20260926.pptx](docs/PRJ_277_Review2_20260926.pptx).
- The overview screen in [docs/ui-captures/overview.png](docs/ui-captures/overview.png) was captured from the hosted dashboard on 26 September 2026. The deck includes a slide-sized crop.
