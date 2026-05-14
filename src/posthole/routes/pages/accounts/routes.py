"""Accounts route: ``/accounts``."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from posthole.core.templates import templates

router = APIRouter()


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_view(request: Request) -> HTMLResponse:
    """Render the accounts view at ``/accounts``."""
    return templates.TemplateResponse(request, "pages/accounts/index.html.j2", {})
