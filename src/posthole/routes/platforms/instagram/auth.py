"""Auth shims for Instagram handlers — lookup-or-raise wrappers around the OAuth store.

Two named shims, one per failure-mode semantic:

- :func:`require_access_token` — publishing's auth gate. Missing/invalid token
  raises :class:`UnauthorizedError` (401, "this endpoint requires auth").
- :func:`require_oauth_token` — OAuth-flow validation (``/me``, ``/access_token``,
  ``/refresh_access_token``). Missing/invalid token raises the caller-supplied
  exception class (defaults to :class:`InvalidAccessTokenError`, 400). The
  optional ``kind=`` arg lets ``/refresh_access_token`` enforce ``kind="long"``
  via the same shim.

Both ultimately delegate to :func:`posthole.db.oauth.get_token`; the db layer
stays return-Optional, exceptions live at the platform boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.db import oauth
from posthole.routes.platforms.instagram.exceptions import (
    InvalidAccessTokenError,
    MetaAPIError,
    UnauthorizedError,
)

if TYPE_CHECKING:
    from posthole.db.database import Database
    from posthole.db.oauth import OAuthToken, TokenKind


def require_access_token(db: Database, token: str) -> OAuthToken:
    """Return the :class:`OAuthToken` for ``token`` or raise :class:`UnauthorizedError` (401)."""
    if not token:
        raise UnauthorizedError
    tok = oauth.get_token(db, token)
    if tok is None:
        raise UnauthorizedError
    return tok


def require_oauth_token(
    db: Database,
    token: str,
    exc_cls: type[MetaAPIError] = InvalidAccessTokenError,
    *,
    kind: TokenKind | None = None,
) -> OAuthToken:
    """OAuth-flow lookup with optional kind check; raise ``exc_cls`` on any failure.

    Used by OAuth handlers where the failure status is 400 (vs publishing's
    401). If ``kind`` is given and the token's kind doesn't match, the same
    ``exc_cls`` is raised — collapses ``/refresh_access_token``'s
    "missing OR wrong-kind" into a single check.
    """
    tok = oauth.get_token(db, token)
    if tok is None:
        raise exc_cls
    if kind is not None and tok.kind != kind:
        raise exc_cls
    return tok
