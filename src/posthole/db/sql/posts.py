"""SQL for the ``posts`` table — read by :mod:`posthole.db.posts`."""

from __future__ import annotations

COUNT_ALL = "SELECT COUNT(*) AS n FROM posts"

COUNT_BY_STATUS = "SELECT status, COUNT(*) AS n FROM posts GROUP BY status"

GET_BY_EXTERNAL_REF = "SELECT * FROM posts WHERE external_ref = ?"

GET_BY_ID = "SELECT * FROM posts WHERE id = ?"

INSERT = (
    "INSERT INTO posts ("
    "id, platform, account_id, caption, status, created_at, "
    "external_ref, media_url, media_type, media_items"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

LIST_RECENT = (
    "SELECT * FROM posts "
    "WHERE (:platform IS NULL OR platform = :platform) "
    "AND (:status IS NULL OR status = :status) "
    "ORDER BY created_at DESC LIMIT :limit"
)

MARK_FAILED = "UPDATE posts SET status = 'failed', failure_reason = ? WHERE id = ?"

MARK_PUBLISHED = "UPDATE posts SET status = 'published', published_at = ? WHERE id = ?"

MARK_PUBLISHED_BY_EXTERNAL_REF = (
    "UPDATE posts SET status = 'published', published_at = ?, platform_post_id = ? "
    "WHERE external_ref = ?"
)
