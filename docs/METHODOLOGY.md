# Methodology

## Collection and preprocessing

Records enter through UTF-8 JSON/CSV, RSS, or manually supplied public URLs. HTML extraction keeps article paragraphs where available. The API retains the collected input alongside cleaned text, source URL, source name, publication date, collection time, and a SHA-256 content hash. Duplicate URLs or normalized title/body hashes are skipped.

The local online research form sends the topic and optional alternate names to Google News RSS and Bing News RSS. The Cloudflare Worker uses Bing News RSS plus configured publisher RSS feeds. Both use the selected date range, language locale, and optional source-domain restrictions. Results are checked against the reported publication date, selected outlet domains, and detected language before capture. Accessible publisher pages are stored with the cleaned article text and original HTML. When a page cannot be captured, a usable provider excerpt is stored and labeled `feed_excerpt`. Each record retains the search terms, source URL, discovery URL, collection method, timestamp, and research-job ID. Only records from that search job are analyzed and clustered in that run.

## Language and relevance

Language detection counts Unicode script ranges for Hindi (Devanagari), Kannada, Tamil, and Telugu and detects Latin-script English. The reported confidence is a script evidence score, not a calibrated probabilistic model. Government of India relevance uses configurable multilingual phrase indicators, returns matched reasons, and does not qualify an article on a politician name alone.

## Article analysis

The local baseline extracts a short opening-text summary, phrase-supported article-tone cues, topic labels, known institution names, claim-like sentences, and sentences containing concern/positive markers. Low-evidence article tone is `uncertain`; article tone is not used as an audience verdict.

These rule-based fields are research aids, not language-calibrated judgments. The model label identifies the local ruleset and language. Topic and entity fields include the triggering text to support inspection.

An optional TypeSafe JEV decision provider can be selected with `ANALYSIS_PROVIDER=typesafe` and `TYPESAFE_API_KEY`. The API sends one bounded request per non-synthetic article, containing its language, title, and up to `JEV_MAX_ARTICLE_CHARS` of text. The request asks for a Government of India relevance probability, article sentiment, and a primary-topic choice. Confidence below `JEV_MIN_CONFIDENCE` leaves sentiment uncertain. JEV output, effective labels, probabilities, token usage, model name, and truncation status are stored in `analysis.evidence.provider_decisions`. JEV does not return quote-level rationales or generate prose; its decisions stay separate from summaries. Synthetic demo articles are never sent to TypeSafe.

An optional Gemini text-generation provider uses `GEMINI_API_KEY` to generate summaries and key points for newly collected non-synthetic articles. It receives a bounded title and article excerpt and returns structured JSON. The application checks every supporting excerpt against the article text before showing it. A generated summary remains a model interpretation rather than a verified fact; unsupported or malformed output falls back to the local extracted summary. The generation provider, model, timestamp, input size, truncation status, and checked excerpts are stored in `analysis.evidence.gemini_generation`. Synthetic demo articles are never sent to Gemini. JEV structured decisions and Gemini prose generation are independent, optional providers.

## Public audience view

For a collected real article, the detail view searches the public Bluesky AppView and Hacker News Search API. Each collected post/comment keeps its original link, exact text, date, platform engagement counts, and match basis; a scan is capped at 12. On Hacker News, a comment is included only when its parent discussion title matches or the discussion links directly to the article. Article tone is never treated as public reaction; synthetic articles are excluded.

JEV classifies each collected post independently as positive, negative, mixed, neutral, or uncertain about the issue described by the article. Low-confidence or missing decisions stay uncertain. Only positive and negative reactions determine whether the sample leans favorable or critical; close counts produce a divided result. Neutral and uncertain reactions are excluded, and mixed reactions are shown but do not determine direction by themselves. Gemini provides an optional sample summary and maps themes to exact collected post text. If JEV is unavailable, Gemini can supply per-post labels; if both are unavailable, the public text remains unlabeled. Engagement is shown for context and does not weight the reaction counts. The scan cache lasts five minutes to limit repeat external calls.

These results describe only the posts returned by the queried services and the URL/headline match rules. They do not estimate the views of all readers or the public. Headline-matched posts can discuss the same issue without responding to the exact article; the UI identifies the match basis and links to every post. News feeds supply reporting but not reader commentary. Reddit, X, and publisher-hosted comment systems are not queried in this release because they need separate credentials or site-specific access.

## Story clustering and comparison

The default embedding provider uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through FastEmbed on CPU. Vectors are persisted and pairwise cosine similarity creates candidate clusters. Known multilingual concept hints enrich the text before embedding to support the five-language demo. If the model cannot load, the pipeline logs the fallback and uses deterministic Unicode token/character features with shared concept hints.

Comparisons aggregate observed topics and article-tone sentiment by language and source. Shared topics/entities include article IDs. Coverage differences name the groups and article sample sizes used. No comparison is labeled objective truth or outlet bias.

## Provenance and interpretation

The trace is: dashboard metric → story cluster → article → source and source URL → raw/clean text → model label, timestamp, confidence, and supporting snippet. Synthetic entries are visibly labeled in the UI and stored with `is_synthetic=true`.

## Online search and local model requirements

With local providers and no secrets configured, analysis and embeddings run locally. With TypeSafe or Gemini enabled, bounded portions of collected, non-synthetic article text are sent to that provider; keep keys in server-side secrets and never expose them to browser code. A Gemini key cannot authenticate to TypeSafe, and a TypeSafe key cannot authenticate to Gemini. Search runs use a bounded per-language result count and preserve a job-scoped sample so researchers can inspect the records collected for a query.
