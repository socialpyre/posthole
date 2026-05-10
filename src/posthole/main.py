"""FastAPI application factory and ASGI lifespan for posthole."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.routing import WebSocketRoute

from posthole import __version__
from posthole.config import get_settings
from posthole.web import pages, system
from posthole.web.templates import TEMPLATES_DIR, build_templates

PKG = Path(__file__).parent
templates = build_templates()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Mount the dev hot-reload watcher when ``POSTHOLE_DEV_RELOAD=1``."""
    settings = get_settings()

    if settings.dev_reload:
        # arel is in the dev dependency-group, not runtime — keep the import inline.
        import arel

        hot = arel.HotReload(
            paths=[
                arel.Path(str(TEMPLATES_DIR)),
                arel.Path(str(PKG / "static")),
            ],
        )
        # NOTE: arel.HotReload is an ASGI app (3-arg callable) but Starlette's
        # add_websocket_route is typed as Callable[[WebSocket], Awaitable[None]].
        # WebSocketRoute accepts ASGI apps directly via Callable[..., Any].
        # Don't refactor to add_websocket_route until Starlette's typing relaxes.
        _app.router.routes.append(WebSocketRoute("/hot-reload", hot, name="hot-reload"))

        await hot.startup()

        try:
            yield
        finally:
            await hot.shutdown()
    else:
        yield


def create_app() -> FastAPI:
    """Build and return the posthole FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="posthole",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.mount("/static", StaticFiles(directory=PKG / "static"), name="static")

    app.include_router(pages.build_router(templates))
    app.include_router(system.router)

    return app


app = create_app()
