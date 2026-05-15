"""Per-request middleware that populates ``request.state`` for templates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from posthole.db import accounts, posts

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request
    from fastapi.responses import Response


class TemplateContextMiddleware(BaseHTTPMiddleware):
    """Stamp template-visible values onto ``request.state``.

    The sidebar is rendered on every page, so its counts are computed
    once per request here rather than threaded through each page's
    context builder.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Populate ``request.state`` for downstream templates."""
        db = getattr(request.app.state, "db", None)
        if db is not None:
            by_status = posts.count_by_status(db)
            request.state.sidebar_counts = {
                "posts": posts.count(db),
                "accounts": accounts.count(db),
                "published": by_status.get("published", 0),
                "pending": by_status.get("pending", 0),
                "failed": by_status.get("failed", 0),
            }
        else:
            request.state.sidebar_counts = {
                "posts": 0,
                "accounts": 0,
                "published": 0,
                "pending": 0,
                "failed": 0,
            }

        # Normalize ?platform= / ?status= once, here, so the sidenav doesn't
        # echo unknown values like ``?status=GARBAGE`` back into the hrefs
        # it generates. The inbox view does its own normalization too — we
        # just need the sidebar to see the cleaned values.
        #
        # Lazy import: ``posthole.routes.pages.posts.context`` pulls in the
        # full routes tree which transitively touches ``core.exceptions``
        # — a module that's still loading when this file is first imported
        # during app construction. Resolving the import here means it runs
        # only at request time, after the import graph has settled.
        from posthole.routes.pages.posts.context import (
            normalize_platform,
            normalize_status,
        )

        request.state.url_filters = {
            "platform": normalize_platform(request.query_params.get("platform")),
            "status": normalize_status(request.query_params.get("status")),
        }
        return await call_next(request)


__all__ = ["TemplateContextMiddleware"]
