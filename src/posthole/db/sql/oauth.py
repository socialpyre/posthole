"""SQL for OAuth state — ``oauth_codes`` and ``oauth_tokens`` tables."""

from __future__ import annotations

DELETE_CODE = "DELETE FROM oauth_codes WHERE code = ?"

INSERT_CODE = (
    "INSERT INTO oauth_codes (code, account_id, redirect_uri, state, issued_at) "
    "VALUES (?, ?, ?, ?, ?)"
)

INSERT_TOKEN = "INSERT INTO oauth_tokens (token, account_id, kind, created_at) VALUES (?, ?, ?, ?)"  # noqa: S105

SELECT_CODE = "SELECT * FROM oauth_codes WHERE code = ?"

SELECT_TOKEN = "SELECT * FROM oauth_tokens WHERE token = ?"  # noqa: S105 — SQL constant

# ``short`` tokens are excluded — they expire too fast to be a useful card stat.
LATEST_LONG_TOKEN_BY_ACCOUNT = (
    "SELECT account_id, kind, MAX(created_at) AS created_at "  # noqa: S105 — SQL constant
    "FROM oauth_tokens "
    "WHERE kind IN ('long', 'refresh') "
    "GROUP BY account_id"
)
