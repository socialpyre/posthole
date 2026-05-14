"""Application-wide exception handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.core.exceptions.types import NotFoundError
from posthole.core.templates import templates

if TYPE_CHECKING:
    from fastapi import Request
    from fastapi.responses import HTMLResponse


async def handle_not_found(request: Request, exc: Exception) -> HTMLResponse:
    """Render the generic not-found page with a 404 status."""
    if not isinstance(exc, NotFoundError):  # pragma: no cover — defensive
        raise exc
    return templates.TemplateResponse(
        request,
        "pages/not_found.html.j2",
        {"resource": exc.resource, "resource_id": exc.resource_id},
        status_code=404,
    )
