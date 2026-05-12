-- Initial schema: the posts table.
--
-- Each row represents one publish attempt against a platform — the central
-- mock-server entity. status transitions: pending -> published | failed.

CREATE TABLE posts (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  account_id TEXT NOT NULL,
  caption TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  published_at TEXT,
  failure_reason TEXT
);

CREATE INDEX idx_posts_created_at ON posts (created_at DESC);
CREATE INDEX idx_posts_account_id ON posts (account_id);
