CREATE TABLE IF NOT EXISTS reaction_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'complete',
  query_text TEXT NOT NULL,
  sample_count INTEGER NOT NULL DEFAULT 0,
  sentiment_distribution TEXT NOT NULL DEFAULT '{}',
  summary TEXT NOT NULL DEFAULT '',
  themes TEXT NOT NULL DEFAULT '[]',
  classifier TEXT,
  summarizer TEXT,
  sources TEXT NOT NULL DEFAULT '[]',
  notes TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public_reactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES reaction_runs(id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  external_id TEXT NOT NULL,
  reaction_text TEXT NOT NULL,
  reaction_url TEXT NOT NULL,
  published_at TEXT,
  engagement_label TEXT NOT NULL DEFAULT 'likes',
  likes INTEGER NOT NULL DEFAULT 0,
  replies INTEGER NOT NULL DEFAULT 0,
  reposts INTEGER NOT NULL DEFAULT 0,
  match_basis TEXT NOT NULL,
  sentiment TEXT NOT NULL DEFAULT 'uncertain',
  confidence REAL NOT NULL DEFAULT 0,
  UNIQUE (run_id, platform, external_id)
);

CREATE INDEX IF NOT EXISTS ix_reaction_runs_article_id ON reaction_runs(article_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_public_reactions_run_id ON public_reactions(run_id);
