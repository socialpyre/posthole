"""Instagram platform wiring — ``name`` + composed top-level router."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from posthole.platforms.instagram import oauth, publishing

if TYPE_CHECKING:
    from fastapi_hotwire import HotwireTemplates


name: str = "instagram"


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Mount Instagram's OAuth + publishing sub-routers."""
    router = APIRouter()
    router.include_router(oauth.build_router(templates))
    router.include_router(publishing.build_router())
    return router
