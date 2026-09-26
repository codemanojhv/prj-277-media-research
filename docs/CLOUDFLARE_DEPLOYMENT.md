# Cloudflare Workers deployment

## Current hosted prototype

The hosted demonstration uses a Next.js 15 application bundled with OpenNext, a Cloudflare Worker for web and API routes, and a D1 SQLite-compatible database for stored sources, articles, analyses, story groups, and job records. It serves from a `workers.dev` address; a custom domain is optional.

The delivered Worker build is under the Cloudflare free-plan prototype path. It does not use Docker, Containers, a remote FastAPI process, or an external database. The Worker-facing API is implemented in `apps/web/lib/cloudflare-api.ts`; the local FastAPI implementation remains the full reference workflow.

## Deploy a separate copy

1. Install Node.js and authenticate Wrangler with an account that has Workers and D1 write access:

   ```powershell
   npx wrangler login
   ```

2. Create a D1 database:

   ```powershell
   cd apps/web
   npx wrangler d1 create prj-277-media-research --location apac
   ```

3. Replace `REPLACE_AFTER_DATABASE_CREATE` in `apps/web/wrangler.jsonc` with the new database ID.

4. From the repository root, run:

   ```powershell
   npm run cf:deploy
   ```

The deployment script applies D1 schema migrations, bundles the Next.js Worker, and deploys it. It does not start a local app/API server, prepare a local SQLite corpus, download model weights, or run a local embedding model. Existing D1 records remain in the remote database. A new empty D1 database can start collecting real articles as soon as the Worker is deployed.

## Optional TypeSafe JEV secret

JEV uses the hosted TypeSafe API for non-synthetic article decisions. Set the secret without putting it in source control or browser code:

```powershell
cd apps/web
npx wrangler secret put TYPESAFE_API_KEY
```

New non-synthetic articles use TypeSafe JEV for Government of India relevance, sentiment, target-specific stance, and primary topic. Synthetic examples do not call model APIs. The Worker sends bounded article text to TypeSafe; the secret stays server-side. Gemini and OpenRouter credentials are not valid TypeSafe credentials.

## Optional Gemini summary generation

Gemini generates neutral summaries and key points for newly collected non-synthetic records. The Worker sends bounded source text, keeps the key server-side, and maps model-selected sentence IDs back to exact stored sentences for evidence. It retries transient service errors and tries Gemini 3.7 Flash if Gemini 3.8 Flash remains unavailable. If Gemini still fails, the record is labeled with the API failure and deterministic text rules provide a limited fallback; no model weights are downloaded. Synthetic demo articles do not call model APIs.

For the deployed Worker, run this from `apps/web` and enter the key only into Wrangler's hidden prompt:

```powershell
npx wrangler secret put GEMINI_API_KEY
```

For optional local Wrangler development, copy `.dev.vars.example` to `.dev.vars` in `apps/web` and add your key there. `.dev.vars` is gitignored. This is not needed to use the hosted app.

Gemini is used for prose generation; TypeSafe JEV remains responsible for optional structured classifications. Configure `TYPESAFE_API_KEY` separately if JEV is also desired. Do not paste either key into source files, the browser, or chat.

## Hosted prototype boundaries

- Google News RSS and Bing News RSS provide a bounded discovery sample; they do not cover all relevant online media.
- The Workers research path groups results from one search job as a candidate coverage set. It does not download or use the local FastEmbed model.
- An inaccessible publisher page may yield a labeled feed excerpt instead of full text.
- The Worker adapter has not had a full security, scale, or human-labeled model evaluation. Do not use it for sensitive data.
- The default records are synthetic and must not be cited as real reporting.

## Deployed university demo

The current hosted app is available at [PRJ_277 on Cloudflare Workers](https://prj-277-media-research.manojhv13.workers.dev/). Both TypeSafe JEV and Gemini have been verified through the hosted provider-status endpoint. A real The Hindu article was collected, analyzed with both APIs, and stored with source-linked evidence in D1. The dashboard also retains labeled synthetic examples for classroom demonstration.
