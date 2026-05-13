"""SQL for the ``posts`` table — read by :mod:`posthole.db.posts`."""

from __future__ import annotations

GET_BY_EXTERNAL_REF = "SELECT * FROM posts WHERE external_ref = ?"

GET_BY_ID = "SELECT * FROM posts WHERE id = ?"

INSERT = (
    "INSERT INTO posts ("
    "id, platform, account_id, caption, status, created_at, "
    "external_ref, media_url, media_type"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

LIST_RECENT = "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?"

MARK_FAILED = "UPDATE posts SET status = 'failed', failure_reason = ? WHERE id = ?"

MARK_PUBLISHED = "UPDATE posts SET status = 'published', published_at = ? WHERE id = ?"

MARK_PUBLISHED_BY_EXTERNAL_REF = (
    "UPDATE posts SET status = 'published', published_at = ?, platform_post_id = ? "
    "WHERE external_ref = ?"
)
