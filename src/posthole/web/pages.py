"""HTML page routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi_hotwire import HotwireTemplates

from posthole.config import get_settings


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Build the page router bound to the given ``templates`` instance."""

    def context() -> dict:
        """Build a fresh template context per request.

        Starlette's ``TemplateResponse`` injects ``request`` via
        ``setdefault``; sharing one dict across requests would pin the
        first request's object and stale every subsequent render.
        """
        return {"DEV_RELOAD": get_settings().dev_reload}

    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def inbox(request: Request) -> HTMLResponse:
        """Render the inbox view at ``/``."""
        return templates.TemplateResponse(
            request,
            "pages/inbox/index.html.j2",
            context(),
        )

    @router.get("/accounts", response_class=HTMLResponse)
    async def accounts(request: Request) -> HTMLResponse:
        """Render the accounts view at ``/accounts``."""
        return templates.TemplateResponse(
            request,
            "pages/accounts/index.html.j2",
            context(),
        )

    @router.get("/scenarios", response_class=HTMLResponse)
    async def scenarios(request: Request) -> HTMLResponse:
        """Render the scenarios view at ``/scenarios``."""
        return templates.TemplateResponse(
            request,
            "pages/scenarios/index.html.j2",
            context(),
        )

    @router.get("/settings", response_class=HTMLResponse)
    async def settings(request: Request) -> HTMLResponse:
        """Render the settings view at ``/settings``."""
        return templates.TemplateResponse(
            request,
            "pages/settings/index.html.j2",
            context(),
        )

    return router
