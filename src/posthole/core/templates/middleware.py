"""Per-request middleware that populates ``request.state`` for templates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request
    from fastapi.responses import Response


class TemplateContextMiddleware(BaseHTTPMiddleware):
    """Stamp template-visible values onto ``request.state``.

    Empty pass-through today; populated as per-request values land.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Extension point — populate ``request.state`` here.

        Examples::

            request.state.request_id = correlation_id.get() or ""
            request.state.current_account = ...
        """
        return await call_next(request)


__all__ = ["TemplateContextMiddleware"]
