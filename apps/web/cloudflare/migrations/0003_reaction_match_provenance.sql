ALTER TABLE reaction_runs ADD COLUMN collector_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE public_reactions ADD COLUMN discussion_title TEXT;
