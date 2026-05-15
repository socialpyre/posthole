"""Accounts: mock identities clients can authorize as."""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from posthole.db.sql import accounts as sql

if TYPE_CHECKING:
    from posthole.db.database import Database


AccountType = str


# sqlite formats UNIQUE-on-(platform, username) failures with this exact
# substring. Matching it lets us discriminate from a PK collision or a
# future composite index touching one of the columns.
_DUP_HANDLE_MARKER = "accounts.platform, accounts.username"


class DuplicateUsernameError(Exception):
    """Raised when ``(platform, username)`` collides with an existing row."""

    def __init__(self, platform: str, username: str) -> None:
        super().__init__(f"username {username!r} already exists for {platform}")
        self.platform = platform
        self.username = username


@dataclass(slots=True)
class Account:
    """A mock identity — the thing a client gets a token for."""

    id: str
    username: str
    display_name: str
    avatar_url: str | None
    account_type: AccountType
    platform: str


@dataclass(slots=True, frozen=True)
class AccountStats:
    """Per-account activity aggregates derived from the ``posts`` table."""

    intercepted_count: int
    last_post_at: datetime | None


def count(db: Database) -> int:
    """Return the total number of accounts."""
    with db.cursor() as cur:
        cur.execute(sql.COUNT_ALL)
        row = cur.fetchone()
    return int(row["n"]) if row else 0


def count_by_platform(db: Database) -> dict[str, int]:
    """Return per-platform account counts (platforms with zero rows are absent)."""
    with db.cursor() as cur:
        cur.execute(sql.COUNT_BY_PLATFORM)
        rows = cur.fetchall()
    return {row["platform"]: int(row["n"]) for row in rows}


def create(
    db: Database,
    *,
    platform: str,
    username: str,
    display_name: str,
    account_type: AccountType,
    avatar_url: str | None = None,
    account_id: str | None = None,
) -> Account:
    """Insert a new mock account; return the hydrated row."""
    acc = Account(
        id=account_id or _generate_id(platform),
        username=username,
        display_name=display_name,
        avatar_url=avatar_url,
        account_type=account_type,
        platform=platform,
    )
    try:
        with db.cursor() as cur:
            cur.execute(
                sql.INSERT,
                (
                    acc.id,
                    acc.username,
                    acc.display_name,
                    acc.avatar_url,
                    acc.account_type,
                    acc.platform,
                ),
            )
    except sqlite3.IntegrityError as e:
        if _DUP_HANDLE_MARKER in str(e):
            raise DuplicateUsernameError(platform, username) from e
        raise
    return acc


def delete(db: Database, account_id: str) -> bool:
    """Delete an account + revoke its tokens. Returns ``True`` if a row was removed."""
    with db.cursor() as cur:
        cur.execute(sql.DELETE_OAUTH_TOKENS_FOR_ACCOUNT, (account_id,))
        cur.execute(sql.DELETE_OAUTH_CODES_FOR_ACCOUNT, (account_id,))
        cur.execute(sql.DELETE_BY_ID, (account_id,))
        return cur.rowcount > 0


def get(db: Database, account_id: str) -> Account | None:
    """Return the account with this id, or ``None``."""
    with db.cursor() as cur:
        cur.execute(sql.GET_BY_ID, (account_id,))
        row = cur.fetchone()
    return _from_row(row) if row else None


def get_by_username(db: Database, username: str) -> Account | None:
    """Return the account with this username, or ``None``."""
    with db.cursor() as cur:
        cur.execute(sql.GET_BY_USERNAME, (username,))
        row = cur.fetchone()
    return _from_row(row) if row else None


def list_all(db: Database, *, platform: str | None = None) -> list[Account]:
    """Return accounts ordered by username. Optionally scoped to one platform."""
    with db.cursor() as cur:
        if platform is None:
            cur.execute(sql.LIST_ALL)
        else:
            cur.execute(sql.LIST_BY_PLATFORM, (platform,))
        rows = cur.fetchall()
    return [_from_row(r) for r in rows]


def stats_by_account(db: Database) -> dict[str, AccountStats]:
    """Return per-account activity aggregates keyed by account id."""
    with db.cursor() as cur:
        cur.execute(sql.STATS_BY_ACCOUNT)
        rows = cur.fetchall()
    return {
        row["account_id"]: AccountStats(
            intercepted_count=int(row["intercepted_count"]),
            last_post_at=datetime.fromisoformat(row["last_post_at"])
            if row["last_post_at"]
            else None,
        )
        for row in rows
    }


def update(
    db: Database,
    account_id: str,
    *,
    username: str,
    display_name: str,
    account_type: AccountType,
) -> Account | None:
    """Update mutable fields on an account; ``None`` if the row is gone."""
    try:
        with db.cursor() as cur:
            cur.execute(sql.UPDATE, (username, display_name, account_type, account_id))
            if cur.rowcount == 0:
                return None
    except sqlite3.IntegrityError as e:
        if _DUP_HANDLE_MARKER in str(e):
            current = get(db, account_id)
            raise DuplicateUsernameError(
                current.platform if current else "unknown", username
            ) from e
        raise
    return get(db, account_id)


def _from_row(row: sqlite3.Row) -> Account:
    """Hydrate an :class:`Account` from a row."""
    return Account(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        avatar_url=row["avatar_url"],
        account_type=row["account_type"],
        platform=row["platform"],
    )


def _generate_id(platform: str) -> str:
    """Mint a platform-shaped account id."""
    if platform == "instagram":
        return f"17841{secrets.randbelow(10**12):012d}"
    if platform == "tiktok":
        return f"tt-{secrets.randbelow(10**19):019d}"
    return f"acc_{secrets.token_hex(8)}"
