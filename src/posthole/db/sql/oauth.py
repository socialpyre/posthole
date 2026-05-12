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
