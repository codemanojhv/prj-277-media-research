# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

University students and researchers studying how public news coverage describes Government of India policies, schemes, and announcements across regional-language media.

## Product Purpose

PRJ_277 helps a researcher describe a topic, choose dates, languages, and outlets, collect available public news results, and inspect how the collected sample compares. Success means the researcher can move from a search request to stored article text, a traceable story comparison, and source-linked evidence.

## Positioning

The product combines multilingual topic discovery with source-level provenance: each comparison can be followed back to the article text, collected URL, discovery source, and analysis record that produced it.

## Operating Context

The researcher enters a campaign, policy, announcement, or headline; may add aliases; chooses a publication window, supported languages, optional outlets, and a result limit; then reviews the stored search job, story groups, article records, text, and evidence in the browser.

## Capabilities and Constraints

- The local application uses Next.js, TypeScript, Tailwind, FastAPI, SQLAlchemy, and SQLite. The requested hosted target is Cloudflare Workers with D1.
- The included 100-article dataset is synthetic classroom material in English, Hindi, Kannada, Tamil, and Telugu. It is not real reporting.
- Online collection uses Google News RSS and Bing News RSS and can miss relevant coverage. Accessible publisher pages may be stored as article text; otherwise a feed excerpt is labeled as such.
- A local evidence-oriented analysis path works without credentials. TypeSafe JEV is an optional structured decision provider for relevance, sentiment, stance, and primary topic; enabling it requires a TypeSafe API key kept server-side.
- JEV does not produce quote-level rationales or summaries. Local text extraction remains separate from JEV decisions. Synthetic records are never sent to JEV.
- Language, relevance, topic, sentiment, stance, and clustering outputs are research aids, not verified facts. Sentiment and target-specific stance remain distinct; weak evidence should remain uncertain.
- Comparisons describe only the collected sample and do not classify outlet bias or quality.

## Evidence on Hand

- The project repository contains the UI, API, tests, methodology notes, and a reproducible 100-record synthetic dataset.
- No human-labeled evaluation corpus, representative media sampling frame, or verified real-world performance benchmark has been supplied.

## Product Principles

- Keep source text and collection provenance visible.
- Keep system decisions distinct from extracted article evidence.
- Prefer an explicit uncertain result over an unsupported label.
- Describe observed coverage in the selected sample without ranking outlets or claiming factual verification.
- Keep the local demo usable without paid model credentials.
