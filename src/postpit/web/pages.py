from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi_hotwire import HotwireTemplates

from postpit.config import get_settings


def build_router(templates: HotwireTemplates) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html.jinja",
            {
                "greeting": "hello, postpit!",
                "DEV_RELOAD": get_settings().dev_reload,
            },
        )

    return router
