"""SQLite-backed storage for posthole.

Stores are flat modules of functions taking ``db: Database`` as the first
arg. Import the modules directly:

    from posthole.db import posts, accounts, oauth

    post = posts.get(db, post_id)
    account = accounts.get(db, account_id)
    token = oauth.issue_token(db, account_id=..., kind="short")
"""

from posthole.db import accounts, oauth, posts
from posthole.db.accounts import Account, AccountType
from posthole.db.database import Database, DbDep, get_db
from posthole.db.oauth import OAuthCode, OAuthToken, TokenKind
from posthole.db.posts import Post, PostStatus

__all__ = [
    "Account",
    "AccountType",
    "Database",
    "DbDep",
    "OAuthCode",
    "OAuthToken",
    "Post",
    "PostStatus",
    "TokenKind",
    "accounts",
    "get_db",
    "oauth",
    "posts",
]
