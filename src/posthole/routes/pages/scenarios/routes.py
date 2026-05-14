"""Scenarios route: ``/scenarios``."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from posthole.core.templates import templates

router = APIRouter()


@router.get("/scenarios", response_class=HTMLResponse)
async def scenarios_view(request: Request) -> HTMLResponse:
    """Render the scenarios view at ``/scenarios``."""
    return templates.TemplateResponse(request, "pages/scenarios/index.html.j2", {})
