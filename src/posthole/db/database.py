"""SQLite connection lifecycle, cursor context manager, migration runner."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request

from posthole.db.migrations import MIGRATIONS
from posthole.db.sql import pragmas, schema_version
from posthole.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Iterator


class Database:
    """A sqlite3 connection wrapper — owns the lifecycle and the cursor context.

    DB access is via flat module-level functions in ``posthole.db.{posts,
    accounts, oauth}``, each taking a ``Database`` as the first arg. This
    object does NOT host store instances.

    Designed for posthole's all-async handler model: every DB call happens on
    the event loop, single-threaded. If a sync route handler is ever added,
    revisit thread-safety — sqlite3 connections are not safe to share across
    threads without serialization.

    ``path`` is operator-controlled (``POSTHOLE_DATABASE_URL`` env var), not
    user input — no path-traversal threat model.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn = sqlite3.connect(
            path,
            isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(pragmas.ENABLE_FOREIGN_KEYS)

        if path != ":memory:":
            # WAL gives concurrent readers + durable writes for file-backed DBs.
            # sqlite rejects WAL on :memory:.
            self._conn.execute(pragmas.ENABLE_WAL)
        self.migrate()

    def close(self) -> None:
        """Close the underlying sqlite3 connection. Idempotent on shutdown."""
        self._conn.close()

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        """Yield a cursor on the shared connection.

        ``isolation_level=None`` means every statement is its own transaction
        and commits immediately — fine for the single-row reads and writes
        we have today. When multi-statement atomic writes appear, wrap them
        in explicit ``BEGIN``/``COMMIT`` (or restructure this method).
        """
        cur = self._conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    def migrate(self) -> None:
        """Apply any MIGRATIONS entries newer than the highest recorded version.

        Called automatically by ``__init__`` so opening a Database always lands
        on the current schema. Idempotent — re-invoking on an up-to-date DB is
        a no-op. Refuses to run if the DB has been written by a newer build
        (e.g., the user downgraded the image): silently running against a
        too-old binary would corrupt data when queries reference columns the
        binary doesn't know about.
        """
        cur = self._conn.cursor()
        try:
            cur.execute(schema_version.CREATE_TABLE)
            cur.execute(schema_version.SELECT_MAX_VERSION)
            row = cur.fetchone()
            current = row[0] if row and row[0] is not None else -1

            latest = len(MIGRATIONS) - 1
            if current > latest:
                msg = (
                    f"Database is at schema version {current} but this posthole "
                    f"build only knows up to version {latest}. You likely "
                    f"downgraded — pin a newer image or restore from backup."
                )
                raise RuntimeError(msg)

            for version, sql in enumerate(MIGRATIONS):
                if version <= current:
                    continue
                cur.executescript(sql)
                cur.execute(schema_version.INSERT_VERSION, (version,))
                logger.info("Migration successfully applied", version=version)
        finally:
            cur.close()


def get_db(request: Request) -> Database:
    """FastAPI dependency — returns the app's Database from ``app.state``."""
    return request.app.state.db


DbDep = Annotated[Database, Depends(get_db)]
