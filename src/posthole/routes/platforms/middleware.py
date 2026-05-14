"""Strip platform API version prefixes (``/v22.0/...``) before route matching.

Real platform clients send versioned URLs — Meta's ``/v22.0/...``, TikTok's
``/v2/...``. The version is purely cosmetic for our mock-server purposes;
this middleware rewrites the path so each platform's route handlers can
match on the clean form (``/me``, ``/oauth/access_token``, etc.) without
declaring versioned variants.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request
    from fastapi.responses import Response


VERSION_PREFIX_RE = re.compile(r"^/v\d+(\.\d+)?(/|$)")

# Paths reserved for posthole itself; versioned variants should NOT be
# rewritten to hit these. ``/_`` covers ``/_health`` (and any future
# underscore-prefixed admin endpoint by convention).
INTERNAL_PATH_PREFIXES: tuple[str, ...] = (
    "/_",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static/",
    "/hot-reload",
)


class VersionStripMiddleware(BaseHTTPMiddleware):
    """Rewrite ``/v22.0/foo`` → ``/foo`` so platform routes see clean paths.

    Should run as the OUTERMOST middleware so every other layer and every
    route handler sees the rewritten path.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Strip the version prefix from ``request.scope["path"]`` if present."""
        path = request.url.path
        if VERSION_PREFIX_RE.match(path):
            stripped = VERSION_PREFIX_RE.sub("/", path, count=1)
            if not stripped.startswith(INTERNAL_PATH_PREFIXES):
                request.scope["path"] = stripped
        return await call_next(request)


__all__ = ["INTERNAL_PATH_PREFIXES", "VERSION_PREFIX_RE", "VersionStripMiddleware"]
