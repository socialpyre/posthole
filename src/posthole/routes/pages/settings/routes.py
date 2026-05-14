"""Settings route: ``/settings``."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from posthole.core.templates import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request) -> HTMLResponse:
    """Render the settings view at ``/settings``."""
    return templates.TemplateResponse(request, "pages/settings/index.html.j2", {})
