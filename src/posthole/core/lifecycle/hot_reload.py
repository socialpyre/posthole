"""Dev-only arel hot-reload watcher for templates and static assets."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from posthole.core.templates import TEMPLATES_DIR

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


STATIC_DIR = TEMPLATES_DIR.parent / "static"


@asynccontextmanager
async def hot_reload(app: FastAPI) -> AsyncIterator[None]:
    """Mount arel's ``/hot-reload`` WebSocket and run its startup/shutdown."""
    import arel
    from starlette.routing import WebSocketRoute

    watcher = arel.HotReload(
        paths=[
            arel.Path(str(TEMPLATES_DIR)),
            arel.Path(str(STATIC_DIR)),
        ],
    )

    # NOTE: arel.HotReload is an ASGI app (3-arg callable) but Starlette's
    # add_websocket_route is typed as Callable[[WebSocket], Awaitable[None]].
    # WebSocketRoute accepts ASGI apps directly via Callable[..., Any].
    # Don't refactor to add_websocket_route until Starlette's typing relaxes.
    app.router.routes.append(WebSocketRoute("/hot-reload", watcher, name="hot-reload"))

    await watcher.startup()
    try:
        yield
    finally:
        await watcher.shutdown()
