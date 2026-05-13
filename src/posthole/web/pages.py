"""HTML page routes.

Handlers pass only handler-specific context dicts. Cross-cutting values:

- Process-static (``DEV_RELOAD``, environment, etc.) — registered as
  Jinja globals in :mod:`posthole.web.templates`.
- Per-request (``request_id``, current account, etc.) — stamped on
  ``request.state`` by :mod:`posthole.web.middleware` and read in
  templates as ``{{ request.state.X }}``.

Neither needs to be threaded through these handlers.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from posthole.web.templates import templates

router = APIRouter()


@router.get("/accounts", response_class=HTMLResponse)
async def accounts(request: Request) -> HTMLResponse:
    """Render the accounts view at ``/accounts``."""
    return templates.TemplateResponse(request, "pages/accounts/index.html.j2", {})


@router.get("/", response_class=HTMLResponse)
async def inbox(request: Request) -> HTMLResponse:
    """Render the inbox view at ``/``."""
    return templates.TemplateResponse(request, "pages/inbox/index.html.j2", {})


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail(post_id: str, request: Request) -> HTMLResponse:
    """Render a single post in the detail pane of the inbox shell.

    Stub: ``post_id`` lookup + detail-pane rendering lands with the inbox
    split-pane feature. For now we just thread the id into the context so
    the route exists and the template can branch on it later.
    """
    return templates.TemplateResponse(
        request,
        "pages/inbox/index.html.j2",
        {"post_id": post_id},
    )


@router.get("/scenarios", response_class=HTMLResponse)
async def scenarios(request: Request) -> HTMLResponse:
    """Render the scenarios view at ``/scenarios``."""
    return templates.TemplateResponse(request, "pages/scenarios/index.html.j2", {})


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request) -> HTMLResponse:
    """Render the settings view at ``/settings``."""
    return templates.TemplateResponse(request, "pages/settings/index.html.j2", {})
