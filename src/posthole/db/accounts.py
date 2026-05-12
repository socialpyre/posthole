"""Accounts: mock identities clients can authorize as.

Default accounts are seeded by migrations: IG accounts come from migration
0001, TikTok accounts from migration 0002. Each row carries a ``platform``
field so each platform's authorize-picker can list only its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from posthole.db.sql import accounts as sql

if TYPE_CHECKING:
    import sqlite3

    from posthole.db.database import Database


# Account categories vary slightly across platforms: IG uses BUSINESS/CREATOR/
# PERSONAL, TikTok uses BUSINESS_ACCOUNT/CREATOR_ACCOUNT/PERSONAL_ACCOUNT.
# Kept as plain str rather than a Literal so each platform's enums coexist.
AccountType = str


@dataclass(slots=True)
class Account:
    """A mock identity — the thing a client gets a token for."""

    id: str
    username: str
    display_name: str
    avatar_url: str | None
    account_type: AccountType
    platform: str


def from_row(row: sqlite3.Row) -> Account:
    """Hydrate an :class:`Account` from an ``accounts`` table row."""
    return Account(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        avatar_url=row["avatar_url"],
        account_type=row["account_type"],
        platform=row["platform"],
    )


class AccountStore:
    """Read access to the ``accounts`` table.

    Read-only today — accounts come from migration seeds. Add ``create`` /
    ``delete`` when an admin UI or seed CLI needs to mutate the set.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, account_id: str) -> Account | None:
        """Return the account with this id, or ``None``."""
        with self._db.cursor() as cur:
            cur.execute(sql.GET_BY_ID, (account_id,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def get_by_username(self, username: str) -> Account | None:
        """Return the account with this username, or ``None``."""
        with self._db.cursor() as cur:
            cur.execute(sql.GET_BY_USERNAME, (username,))
            row = cur.fetchone()
        return from_row(row) if row else None

    def list_all(self, *, platform: str | None = None) -> list[Account]:
        """Return accounts ordered by username. Optionally scoped to one platform."""
        with self._db.cursor() as cur:
            if platform is None:
                cur.execute(sql.LIST_ALL)
            else:
                cur.execute(sql.LIST_BY_PLATFORM, (platform,))
            rows = cur.fetchall()
        return [from_row(r) for r in rows]
