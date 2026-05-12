"""Instagram platform wiring — ``name`` + composed top-level router + exception handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from posthole.platforms.instagram import oauth, publishing
from posthole.platforms.instagram.exceptions import MetaAPIError, meta_exception_handler

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi_hotwire import HotwireTemplates


name: str = "instagram"


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Mount Instagram's OAuth + publishing sub-routers."""
    router = APIRouter()
    router.include_router(oauth.build_router(templates))
    router.include_router(publishing.build_router())
    return router


def install_exception_handlers(app: FastAPI) -> None:
    """Register the Meta-shaped exception handler on ``app``."""
    app.add_exception_handler(MetaAPIError, meta_exception_handler)
