"""Posts-page exception handler: renders the inbox shell with the not-found pane."""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.core.templates import templates
from posthole.routes.pages.posts.context import inbox_context
from posthole.routes.pages.posts.exceptions import PostNotFoundError

if TYPE_CHECKING:
    from fastapi import Request
    from fastapi.responses import HTMLResponse


async def handle_post_not_found(request: Request, exc: Exception) -> HTMLResponse:
    """Render the inbox shell with ``not_found=True`` and a 404 status."""
    if not isinstance(exc, PostNotFoundError):  # pragma: no cover — defensive
        raise exc

    ctx = inbox_context(
        request.app.state.db,
        not_found=True,
        q=request.query_params.get("q"),
        view=request.query_params.get("view"),
    )

    return templates.TemplateResponse(
        request,
        "pages/posts/index.html.j2",
        ctx,
        status_code=404,
    )
