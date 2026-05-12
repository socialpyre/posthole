"""Schema migrations loaded from ordered ``.sql`` files in this package.

Each migration is a single ``.sql`` file named ``NNNN_description.sql`` where
``NNNN`` is the zero-padded version number (``0000_initial.sql``,
``0001_add_media.sql``, ...). The on-disk position in ``schema_version`` is
the integer extracted from that prefix.

Rules:
- Append-only. Once a migration ships in a release, never edit it.
- Numbers must be contiguous starting at 0 (the loader rejects gaps).
- Each file is applied via ``executescript`` so multi-statement DDL works;
  semicolon-terminate every statement.

The runner in :mod:`posthole.db.database` reads ``MIGRATIONS`` below, which
is indexed by version — ``MIGRATIONS[N]`` is the SQL for version ``N``.
"""

from posthole.db.migrations.loader import MIGRATIONS, load

__all__ = ["MIGRATIONS", "load"]
