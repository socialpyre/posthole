"""Console entrypoint for ``python -m posthole``.

Bare invocation launches the ASGI server (preserves the
``docker-compose`` UX). The ``migrate`` subcommand applies (or previews)
pending schema migrations against ``POSTHOLE_DATABASE_URL`` — useful for
init containers that want explicit control over when schema changes land.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import uvicorn

from posthole.config import get_settings
from posthole.db.migrations import MIGRATIONS
from posthole.logging import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(prog="posthole")
    sub = parser.add_subparsers(dest="command")

    migrate = sub.add_parser("migrate", help="Apply pending schema migrations.")
    migrate.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pending migrations without applying them.",
    )

    seed = sub.add_parser(
        "seed",
        help="Insert sample posts via the in-process API.",
    )
    seed.add_argument(
        "platform",
        nargs="?",
        default=None,
        help="Optional platform name (e.g. 'instagram', 'tiktok'). Default: all platforms.",
    )

    args = parser.parse_args()

    if args.command == "migrate":
        return _migrate_command(dry_run=args.dry_run)

    if args.command == "seed":
        return _seed_command(platform=args.platform)

    # No subcommand — launch the server.
    settings = get_settings()
    uvicorn.run("posthole.main:app", host=settings.host, port=settings.port)
    return 0


def _seed_command(*, platform: str | None) -> int:
    """Run the in-process seeder against the configured database."""
    from posthole import seed

    try:
        created = seed.run(platform=platform)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    scope = f" ({platform})" if platform else ""
    print(f"Seeded {created} post(s){scope} via the in-process API.")
    return 0


def _migrate_command(*, dry_run: bool) -> int:
    """Apply or preview pending migrations, then exit.

    Output is two-stream by design:
    - ``applied migration version=N`` events go through structlog (so they
      land in the same place as the server's logs)
    - The human-readable summary ("Database at version N. Would apply ...")
      goes through ``print`` to stdout, and downgrade errors to stderr.
      Plain text on the CLI is for the operator, not the log aggregator.
    """
    settings = get_settings()
    configure_logging(
        service="posthole",
        env=settings.environment,
        log_format=settings.log_format,
        log_level=settings.log_level,
    )

    path = settings.database_url
    current = _read_current_version(path)
    latest = len(MIGRATIONS) - 1

    if current > latest:
        print(
            f"ERROR: database at schema version {current} but this build only "
            f"knows up to {latest}. You likely downgraded — pin a newer image "
            f"or restore from backup.",
            file=sys.stderr,
        )
        return 1

    pending = [(v, sql) for v, sql in enumerate(MIGRATIONS) if v > current]

    if not pending:
        print(f"Database at version {current}. No migrations to apply.")
        return 0

    if dry_run:
        print(f"Database at version {current}. Would apply {len(pending)} migration(s):")
        for v, sql in pending:
            first_line = next((line for line in sql.splitlines() if line.strip()), "(empty)")
            print(f"  {v}: {first_line.strip()}")
        return 0

    # Constructing Database runs `migrate()` in __init__, which applies the
    # pending entries and logs each one via structlog.
    from posthole.db import Database

    db = Database(path)
    db.close()
    print(f"Applied {len(pending)} migration(s). Database at version {latest}.")
    return 0


def _read_current_version(path: str) -> int:
    """Read MAX(schema_version) without applying anything or creating the file.

    Intentionally duplicates the read inside ``Database.migrate`` so that
    ``--dry-run`` is genuinely side-effect-free (no DB file created on a
    typo'd path, no WAL files written). If the schema_version table shape
    ever changes, keep these two readers in sync.
    """
    if path != ":memory:" and not Path(path).exists():
        return -1

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        if cur.fetchone() is None:
            return -1
        cur.execute("SELECT MAX(version) FROM schema_version")
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else -1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
