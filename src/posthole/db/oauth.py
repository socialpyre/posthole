"""OAuth state: one-shot authorization codes and longer-lived access tokens.

Platform-agnostic — codes and tokens link to an ``account_id`` but carry no
platform field. Each platform passes its own ``prefix`` when minting tokens
(IG uses ``mock-short-`` / ``mock-long-``; TikTok uses ``act.`` / ``rft.``)
so values are distinguishable at a glance.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from posthole.db.sql import oauth as sql

if TYPE_CHECKING:
    import sqlite3

    from posthole.db.database import Database


TokenKind = Literal["short", "long", "refresh"]


@dataclass(slots=True)
class OAuthCode:
    """A one-shot authorization code — consumed on token exchange."""

    code: str
    account_id: str
    redirect_uri: str
    state: str
    issued_at: datetime


@dataclass(slots=True)
class OAuthToken:
    """A bearer token bound to an account; either short-lived or long-lived."""

    token: str
    account_id: str
    kind: TokenKind
    created_at: datetime


def consume_code(db: Database, code: str) -> OAuthCode | None:
    """Look up a code, then delete it. Returns the context, or ``None`` if unknown.

    Codes are one-shot — re-presenting a consumed code returns ``None``.
    """
    with db.cursor() as cur:
        cur.execute(sql.SELECT_CODE, (code,))
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(sql.DELETE_CODE, (code,))
    return _code_from_row(row)


def get_code(db: Database, code: str) -> OAuthCode | None:
    """Look up a code without consuming it."""
    with db.cursor() as cur:
        cur.execute(sql.SELECT_CODE, (code,))
        row = cur.fetchone()
    return _code_from_row(row) if row else None


def get_token(db: Database, token: str) -> OAuthToken | None:
    """Look up a token by its opaque value."""
    with db.cursor() as cur:
        cur.execute(sql.SELECT_TOKEN, (token,))
        row = cur.fetchone()
    return _token_from_row(row) if row else None


def issue_code(db: Database, *, account_id: str, redirect_uri: str, state: str) -> OAuthCode:
    """Mint a fresh authorization code bound to ``account_id``."""
    ctx = OAuthCode(
        code=f"mock-code-{secrets.token_urlsafe(16)}",
        account_id=account_id,
        redirect_uri=redirect_uri,
        state=state,
        issued_at=datetime.now(UTC),
    )
    with db.cursor() as cur:
        cur.execute(
            sql.INSERT_CODE,
            (ctx.code, ctx.account_id, ctx.redirect_uri, ctx.state, ctx.issued_at.isoformat()),
        )
    return ctx


def issue_token(
    db: Database, *, account_id: str, kind: TokenKind, prefix: str | None = None
) -> OAuthToken:
    """Mint a fresh token bound to ``account_id``.

    ``kind`` is the token's role; ``prefix`` is the visible string prefix
    the platform wants on the token value. If ``prefix`` is omitted we pick
    a sensible default per kind.
    """
    if prefix is None:
        prefix = {"short": "mock-short-", "long": "mock-long-", "refresh": "mock-refresh-"}[kind]
    tok = OAuthToken(
        token=f"{prefix}{secrets.token_urlsafe(20)}",
        account_id=account_id,
        kind=kind,
        created_at=datetime.now(UTC),
    )
    with db.cursor() as cur:
        cur.execute(
            sql.INSERT_TOKEN,
            (tok.token, tok.account_id, tok.kind, tok.created_at.isoformat()),
        )
    return tok


def _code_from_row(row: sqlite3.Row) -> OAuthCode:
    """Hydrate an :class:`OAuthCode` from an ``oauth_codes`` row."""
    return OAuthCode(
        code=row["code"],
        account_id=row["account_id"],
        redirect_uri=row["redirect_uri"],
        state=row["state"],
        issued_at=datetime.fromisoformat(row["issued_at"]),
    )


def _token_from_row(row: sqlite3.Row) -> OAuthToken:
    """Hydrate an :class:`OAuthToken` from an ``oauth_tokens`` row."""
    return OAuthToken(
        token=row["token"],
        account_id=row["account_id"],
        kind=row["kind"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
