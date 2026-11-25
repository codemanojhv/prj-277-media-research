# Setup

Install Python 3.12, Node.js/npm, and `uv`, then run `npm run demo` from the project root. On first launch the command installs Python and frontend dependencies, applies Alembic migrations, generates the synthetic data, processes it, and starts FastAPI plus Next.js. It binds to localhost and requires no API keys.

Open **Search coverage** in the app to search news by a topic, date range, language, and optional outlet set. It discovers articles with Google News RSS and Bing News RSS. Gemini and OpenRouter keys are not required; summaries and analysis use the local evidence-oriented baseline, and embeddings run locally.

Optional shared defaults can be placed in a root `.env` copied from `.env.example`. No keys are needed for local fallback. To use JEV in the local FastAPI demo, set `ANALYSIS_PROVIDER=typesafe` and `TYPESAFE_API_KEY`. Individual users can set their Gemini model/key and Scrape Creators key from **Provider keys**; those keys stay in the current browser tab's session storage and are sent only with requests that use the service. On a shared device, remove the keys before closing the tab. `GOI_RELEVANCE_THRESHOLD` defaults to `0.55`; `EMBEDDING_MODEL` defaults to the multilingual MiniLM model; `API_PORT` and `WEB_PORT` can be set in the shell to change the local ports. For shared Cloudflare defaults, use Wrangler secrets as described in [Cloudflare deployment](CLOUDFLARE_DEPLOYMENT.md).

The first model load may download open-source model assets. They are cached locally for later runs. If that load fails, article processing continues with an explicitly labeled lexical fallback.
