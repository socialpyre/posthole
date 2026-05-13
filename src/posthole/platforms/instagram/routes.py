"""Instagram platform — composed top-level router.

The router merges the OAuth and publishing sub-routers. Mounted by
``main.py`` after the UI/system routers so admin paths win first-match
resolution before IG's single-segment wildcard ``GET /{container_id}``.
"""

from __future__ import annotations

from fastapi import APIRouter

from posthole.platforms.instagram import oauth, publishing

router = APIRouter()
router.include_router(oauth.router)
router.include_router(publishing.router)
