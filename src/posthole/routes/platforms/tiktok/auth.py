"""Auth shims for TikTok handlers — Bearer-header parsing + lookup-or-raise.

Handlers call ``require_bearer(db, authorization)`` and proceed with the
returned ``OAuthToken``. Missing header → :class:`MissingBearerHeaderError`;
unknown token → :class:`AccessTokenInvalidError`. Both surface through
:func:`tiktok_exception_handler`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.db import oauth
from posthole.routes.platforms.tiktok._bearer import strip_bearer
from posthole.routes.platforms.tiktok.exceptions import (
    AccessTokenInvalidError,
    MissingBearerHeaderError,
)

if TYPE_CHECKING:
    from posthole.db.database import Database
    from posthole.db.oauth import OAuthToken


def require_bearer(db: Database, authorization: str) -> OAuthToken:
    """Return the :class:`OAuthToken` for the Bearer header, or raise."""
    bearer = strip_bearer(authorization)
    if not bearer:
        raise MissingBearerHeaderError
    tok = oauth.get_token(db, bearer)
    if tok is None:
        raise AccessTokenInvalidError
    return tok
