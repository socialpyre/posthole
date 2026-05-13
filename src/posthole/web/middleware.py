"""Per-request middleware that populates ``request.state`` for templates.

This module owns the seam between "things that vary per request" and the
Jinja templates that want to render them. Anything stamped onto
``request.state`` in :func:`_populate_request_state` becomes available
in templates as ``{{ request.state.X }}`` without per-handler plumbing —
``HotwireTemplates.TemplateResponse(request, ...)`` already injects
``request`` into the context.

Rules of thumb:

- **Per-request values** (correlation_id, authenticated account, theme
  override): stamp here.
- **Process-static values** (settings flags, build version, env name):
  register as Jinja globals in :mod:`posthole.web.templates` instead.

The middleware is intentionally empty today — it's the documented home
for future per-request values. Wired up in :mod:`posthole.main` so the
pattern is in place when ``current_account`` / ``request_id`` / etc.
arrive.

Example of how the next addition will look::

    from asgi_correlation_id.context import correlation_id


    async def _populate_request_state(request, call_next):
        request.state.request_id = correlation_id.get() or ""
        return await call_next(request)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI, Request
    from fastapi.responses import Response


def install_template_context_middleware(app: FastAPI) -> None:
    """Register :func:`_populate_request_state` as an HTTP middleware on ``app``.

    Order matters in :mod:`posthole.main`: this runs AFTER the correlation
    middleware so ``correlation_id.get()`` is populated by the time we
    might read it, and BEFORE route handlers so they see a finalized
    ``request.state``.
    """
    app.middleware("http")(_populate_request_state)


async def _populate_request_state(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Stamp template-visible values onto ``request.state``.

    Empty pass-through today; populated as per-request values land.
    """
    # Extension point — populate request.state here. Examples:
    #   request.state.request_id = correlation_id.get() or ""
    #   request.state.current_account = ...
    return await call_next(request)
