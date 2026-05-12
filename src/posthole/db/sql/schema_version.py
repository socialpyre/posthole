"""SQL for the migration-tracking ``schema_version`` table.

This is meta-machinery the migration runner uses; the table itself isn't
created by a migration, it's created on every Database open (idempotently).
"""

from __future__ import annotations

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
)
"""

INSERT_VERSION = "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))"

SELECT_MAX_VERSION = "SELECT MAX(version) FROM schema_version"
