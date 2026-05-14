"""ASGI lifespan: open the DB on startup, mount hot-reload in dev, close on shutdown."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from posthole.core.config import get_settings
from posthole.core.lifecycle.hot_reload import hot_reload
from posthole.db import Database

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the database and (in dev) mount the hot-reload watcher."""
    settings = get_settings()
    app.state.db = Database(settings.database_url)

    try:
        if settings.dev_reload:
            async with hot_reload(app):
                yield
        else:
            yield
    finally:
        app.state.db.close()
