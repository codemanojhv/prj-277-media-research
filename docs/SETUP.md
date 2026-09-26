# Setup

Install Python 3.12, Node.js/npm, and `uv`, then run `npm run demo` from the project root. On first launch the command installs Python and frontend dependencies, applies Alembic migrations, generates the synthetic data, processes it, and starts FastAPI plus Next.js. It binds to localhost and requires no API keys.

Open **Search coverage** in the app to search news by a topic, date range, language, and optional outlet set. It discovers articles with Google News RSS and Bing News RSS. Gemini and OpenRouter keys are not required; summaries and analysis use the local evidence-oriented baseline, and embeddings run locally.

Optional settings can be placed in a root `.env` copied from `.env.example`. No keys are needed for the local fallback. To use JEV in the local FastAPI demo, set `ANALYSIS_PROVIDER=typesafe` and `TYPESAFE_API_KEY`. To add Gemini summaries, set `GEMINI_API_KEY`; it can be used independently or together with JEV. Keys stay on the API server and are never sent to the browser. `GOI_RELEVANCE_THRESHOLD` defaults to `0.55`; `EMBEDDING_MODEL` defaults to the multilingual MiniLM model; `API_PORT` and `WEB_PORT` can be set in the shell to change the local ports. For Cloudflare Workers, configure the same secrets with `wrangler secret put` from `apps/web` as described in [Cloudflare deployment](CLOUDFLARE_DEPLOYMENT.md).

The first model load may download open-source model assets. They are cached locally for later runs. If that load fails, article processing continues with an explicitly labeled lexical fallback.
