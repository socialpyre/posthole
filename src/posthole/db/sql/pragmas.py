"""PRAGMA statements applied to every sqlite3 connection at open."""

from __future__ import annotations

ENABLE_FOREIGN_KEYS = "PRAGMA foreign_keys = ON"

ENABLE_WAL = "PRAGMA journal_mode = WAL"
