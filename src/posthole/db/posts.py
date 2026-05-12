"""Posts: the central mock-server entity (a publish attempt against a platform)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from posthole.db.sql import posts as sql

if TYPE_CHECKING:
    import sqlite3

    from posthole.db.database import Database


PostStatus = Literal["pending", "published", "failed"]
MediaType = Literal["IMAGE", "VIDEO"]


@dataclass(slots=True)
class Post:
    """One publish attempt against a platform — the central mock-server entity.

    ``external_ref`` is the opaque identifier the platform mints for the
    pending publish (IG's "container_id", TikTok's "publish_id"). ``media_url``
    points at the source image/video. ``platform_post_id`` is the final
    platform-side identifier returned once the publish completes.
    """

    id: str
    platform: str
    account_id: str
    caption: str | None
    status: PostStatus
    created_at: datetime
    published_at: datetime | None
    failure_reason: str | None
    external_ref: str | None
    media_url: str | None
    media_type: MediaType | None
    platform_post_id: str | None


def from_row(row: sqlite3.Row) -> Post:
    """Hydrate a :class:`Post` from a ``posts`` table row."""
    return Post(
        id=row["id"],
        platform=row["platform"],
        account_id=row["account_id"],
        caption=row["caption"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        published_at=parse_iso(row["published_at"]),
        failure_reason=row["failure_reason"],
        external_ref=row["external_ref"],
        media_url=row["media_url"],
        media_type=row["media_type"],
        platform_post_id=row["platform_post_id"],
    )


def iso(dt: datetime) -> str:
    """Serialize a datetime as ISO 8601 for storage in a TEXT column."""
    return dt.isoformat()


def parse_iso(s: str | None) -> datetime | None:
    """Parse an optional ISO 8601 string back into a datetime (or ``None``)."""
    return datetime.fromisoformat(s) if s else None


class PostStore:
    """Read/write access to the ``posts`` table."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        *,
        platform: str,
        account_id: str,
        caption: str | None = None,
        external_ref: str | None = None,
        media_url: str | None = None,
        media_type: MediaType | None = None,
    ) -> Post:
        """Insert a new post in ``pending`` status; return the hydrated row."""
        post = Post(
            id=str(uuid.uuid4()),
            platform=platform,
            account_id=account_id,
            caption=caption,
            status="pending",
            created_at=datetime.now(UTC),
            published_at=None,
            failure_reason=None,
            external_ref=external_ref,
            media_url=media_url,
            media_type=media_type,
            platform_post_id=None,
        )
        with self._db.cursor() as cur:
            cur.execute(
                sql.INSERT,
                (
                    post.id,
                    post.platform,
                    post.account_id,
                    post.caption,
                    post.status,
                    iso(post.created_at),
                    post.external_ref,
                    post.media_url,
                    post.media_type,
                ),
            )
        return post

    def get(self, post_id: str) -> Post | None:
        """Return the post with this id, or ``None`` if none exists."""
        with self._db.cursor() as cur:
            cur.execute(sql.GET_BY_ID, (post_id,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def get_by_external_ref(self, external_ref: str) -> Post | None:
        """Return the post with this platform-minted external reference, or ``None``."""
        with self._db.cursor() as cur:
            cur.execute(sql.GET_BY_EXTERNAL_REF, (external_ref,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def list_recent(self, *, limit: int = 50) -> list[Post]:
        """Return up to ``limit`` posts ordered by ``created_at`` descending."""
        with self._db.cursor() as cur:
            cur.execute(sql.LIST_RECENT, (limit,))
            rows = cur.fetchall()
        return [from_row(r) for r in rows]

    def mark_failed(self, post_id: str, reason: str) -> Post | None:
        """Transition ``post_id`` to ``failed`` with the given reason; ``None`` if missing."""
        with self._db.cursor() as cur:
            cur.execute(sql.MARK_FAILED, (reason, post_id))
            if cur.rowcount == 0:
                return None
            cur.execute(sql.GET_BY_ID, (post_id,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def mark_published(self, post_id: str) -> Post | None:
        """Transition ``post_id`` to ``published`` with current timestamp; ``None`` if missing."""
        with self._db.cursor() as cur:
            cur.execute(sql.MARK_PUBLISHED, (iso(datetime.now(UTC)), post_id))
            if cur.rowcount == 0:
                return None
            cur.execute(sql.GET_BY_ID, (post_id,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def mark_published_by_external_ref(
        self, external_ref: str, platform_post_id: str
    ) -> Post | None:
        """Transition the post with this external_ref to ``published``; ``None`` if missing.

        Used by both Instagram (container_id) and TikTok (publish_id) publish
        flows — the client passes the platform-minted intermediate id and we
        mint the final ``platform_post_id``.
        """
        with self._db.cursor() as cur:
            cur.execute(
                sql.MARK_PUBLISHED_BY_EXTERNAL_REF,
                (iso(datetime.now(UTC)), platform_post_id, external_ref),
            )
            if cur.rowcount == 0:
                return None
            cur.execute(sql.GET_BY_EXTERNAL_REF, (external_ref,))
            row = cur.fetchone()
        return from_row(row) if row else None
