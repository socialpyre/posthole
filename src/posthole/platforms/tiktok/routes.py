"""TikTok platform wiring — ``name`` + composed top-level router + exception handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from posthole.platforms.tiktok import oauth, publishing
from posthole.platforms.tiktok.exceptions import TikTokAPIError, tiktok_exception_handler

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi_hotwire import HotwireTemplates


name: str = "tiktok"


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Mount TikTok's OAuth + publishing sub-routers."""
    router = APIRouter()
    router.include_router(oauth.build_router(templates))
    router.include_router(publishing.build_router())
    return router


def install_exception_handlers(app: FastAPI) -> None:
    """Register the TikTok-shaped exception handler on ``app``."""
    app.add_exception_handler(TikTokAPIError, tiktok_exception_handler)
