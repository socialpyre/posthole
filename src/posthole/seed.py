"""Seed dispatcher — runs each platform's ``seed_flow`` against the in-process app.

Each platform owns its own seed list and flow under
``platforms/<name>/seed.py``. This module's job is just to:

1. Open a Database against the configured ``database_url`` (the FastAPI
   lifespan does not run under ASGITransport, so ``app.state.db`` needs
   to be set manually).
2. Build an in-process httpx client.
3. Iterate :data:`posthole.platforms.PLATFORMS`, calling each platform's
   ``seed_flow`` (or just the one named if a filter is supplied).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

from posthole.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


async def seed_via_app(app: FastAPI, *, platform: str | None = None) -> int:
    """Seed every platform (or just ``platform`` if supplied). Returns total posts.

    Raises ``ValueError`` if ``platform`` is supplied but doesn't match a
    known platform name.
    """
    from posthole.config import get_settings
    from posthole.db import Database
    from posthole.platforms import PLATFORMS

    if platform is not None:
        known = {p.name for p in PLATFORMS}
        if platform not in known:
            msg = f"unknown platform {platform!r}; known: {sorted(known)}"
            raise ValueError(msg)

    settings = get_settings()
    app.state.db = Database(settings.database_url)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://seed") as client:
            total = 0
            for plat in PLATFORMS:
                if platform is not None and plat.name != platform:
                    continue
                count = await plat.seed_flow(client)
                logger.info("seed platform complete", platform=plat.name, count=count)
                total += count
            return total
    finally:
        app.state.db.close()


def run(platform: str | None = None) -> int:
    """Synchronous entry for ``posthole seed [platform]``; returns # posts created."""
    from posthole.main import create_app

    return asyncio.run(seed_via_app(create_app(), platform=platform))
