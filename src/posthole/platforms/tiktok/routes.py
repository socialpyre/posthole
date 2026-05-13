"""TikTok platform — composed top-level router."""

from __future__ import annotations

from fastapi import APIRouter

from posthole.platforms.tiktok import oauth, publishing

router = APIRouter()
router.include_router(oauth.router)
router.include_router(publishing.router)
