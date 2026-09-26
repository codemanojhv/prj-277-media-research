# Data schema

| Table | Purpose | Key trace fields |
|---|---|---|
| `sources` | Outlet/feed identity | name, domain, language, region, type, RSS URL |
| `articles` | Collected/synthetic article | source, URL, title, raw and clean content, author, publication date, language confidence, region, hash, synthetic flag, collected/processed timestamps |
| `article_analysis` | Article-level derived fields | GoI relevance and reasons, summary, sentiment, target/stance, topics, entities, claims, concerns, positive aspects, confidence/evidence, model, timestamp |
| `embeddings` | Local vector cache | article, embedding model, vector, creation timestamp |
| `stories` | Candidate event clusters | canonical title, summary, relevance, first/last seen |
| `story_articles` | Cluster membership | story, article, similarity score |
| `processing_jobs` | Processing run state | type, status, progress, timestamps, error, output metadata |

Indexes cover article source, URL, publication date, language, region, content hash, analysis dimensions, job status, and story membership. SQLite stores vectors as JSON arrays for the local prototype.
