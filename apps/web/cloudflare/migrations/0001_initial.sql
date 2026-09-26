CREATE TABLE IF NOT EXISTS app_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  domain TEXT,
  language TEXT NOT NULL,
  region TEXT,
  source_type TEXT NOT NULL DEFAULT 'news',
  rss_url TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  progress INTEGER NOT NULL DEFAULT 0,
  started_at TEXT,
  completed_at TEXT,
  error TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  raw_content TEXT NOT NULL,
  clean_content TEXT NOT NULL,
  author TEXT,
  published_at TEXT NOT NULL,
  language TEXT NOT NULL,
  language_confidence REAL NOT NULL DEFAULT 0,
  region TEXT,
  content_hash TEXT NOT NULL UNIQUE,
  is_synthetic INTEGER NOT NULL DEFAULT 0,
  collection_method TEXT NOT NULL DEFAULT 'dataset_upload',
  content_kind TEXT NOT NULL DEFAULT 'article_page',
  search_query TEXT,
  discovery_url TEXT,
  research_job_id INTEGER REFERENCES processing_jobs(id),
  collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at TEXT
);

CREATE TABLE IF NOT EXISTS article_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
  goi_relevance_score REAL NOT NULL DEFAULT 0,
  is_goi_relevant INTEGER NOT NULL DEFAULT 0,
  relevance_reasons TEXT NOT NULL DEFAULT '[]',
  sentiment TEXT NOT NULL DEFAULT 'uncertain',
  sentiment_score REAL NOT NULL DEFAULT 0,
  sentiment_confidence REAL NOT NULL DEFAULT 0,
  stance TEXT NOT NULL DEFAULT 'unclear',
  stance_target TEXT NOT NULL DEFAULT 'Union Government policy',
  stance_confidence REAL NOT NULL DEFAULT 0,
  summary TEXT NOT NULL DEFAULT '',
  key_points TEXT NOT NULL DEFAULT '[]',
  topics TEXT NOT NULL DEFAULT '[]',
  entities TEXT NOT NULL DEFAULT '[]',
  claims TEXT NOT NULL DEFAULT '[]',
  concerns TEXT NOT NULL DEFAULT '[]',
  positive_aspects TEXT NOT NULL DEFAULT '[]',
  evidence TEXT NOT NULL DEFAULT '{}',
  model TEXT NOT NULL DEFAULT 'local-evidence-v1',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_key TEXT UNIQUE,
  canonical_title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  goi_relevance REAL NOT NULL DEFAULT 0,
  first_seen TEXT NOT NULL,
  last_updated TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  similarity_score REAL NOT NULL DEFAULT 1,
  UNIQUE(story_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_articles_source_id ON articles(source_id);
CREATE INDEX IF NOT EXISTS ix_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS ix_articles_language ON articles(language);
CREATE INDEX IF NOT EXISTS ix_articles_research_job_id ON articles(research_job_id);
CREATE INDEX IF NOT EXISTS ix_story_articles_story_id ON story_articles(story_id);
CREATE INDEX IF NOT EXISTS ix_story_articles_article_id ON story_articles(article_id);
CREATE INDEX IF NOT EXISTS ix_processing_jobs_status ON processing_jobs(status);
