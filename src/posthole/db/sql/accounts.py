"""SQL for the ``accounts`` table — read by :mod:`posthole.db.accounts`."""

from __future__ import annotations

COUNT_ALL = "SELECT COUNT(*) AS n FROM accounts"

GET_BY_ID = "SELECT * FROM accounts WHERE id = ?"

GET_BY_USERNAME = "SELECT * FROM accounts WHERE username = ?"

LIST_ALL = "SELECT * FROM accounts ORDER BY platform, username"

LIST_BY_PLATFORM = "SELECT * FROM accounts WHERE platform = ? ORDER BY username"
