"""SQL for the ``accounts`` table — read by :mod:`posthole.db.accounts`."""

from __future__ import annotations

COUNT_ALL = "SELECT COUNT(*) AS n FROM accounts"

COUNT_BY_PLATFORM = "SELECT platform, COUNT(*) AS n FROM accounts GROUP BY platform"

DELETE_BY_ID = "DELETE FROM accounts WHERE id = ?"

# oauth_codes / oauth_tokens have no FK to accounts, so cascade in app code.
DELETE_OAUTH_CODES_FOR_ACCOUNT = "DELETE FROM oauth_codes WHERE account_id = ?"
DELETE_OAUTH_TOKENS_FOR_ACCOUNT = "DELETE FROM oauth_tokens WHERE account_id = ?"

GET_BY_ID = "SELECT * FROM accounts WHERE id = ?"

GET_BY_USERNAME = "SELECT * FROM accounts WHERE username = ?"

INSERT = (
    "INSERT INTO accounts (id, username, display_name, avatar_url, account_type, platform) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)

LIST_ALL = "SELECT * FROM accounts ORDER BY platform, username"

LIST_BY_PLATFORM = "SELECT * FROM accounts WHERE platform = ? ORDER BY username"

STATS_BY_ACCOUNT = (
    "SELECT account_id, "
    "       COUNT(*) AS intercepted_count, "
    "       MAX(created_at) AS last_post_at "
    "FROM posts "
    "GROUP BY account_id"
)

UPDATE = "UPDATE accounts SET username = ?, display_name = ?, account_type = ? WHERE id = ?"
