"""FastAPI application factory and ASGI lifespan for posthole."""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.routing import WebSocketRoute

from posthole import __version__
from posthole.config import get_settings
from posthole.db import Database
from posthole.logging import configure_logging, install_correlation_middleware
from posthole.platforms import PLATFORMS
from posthole.web import pages, system
from posthole.web.templates import TEMPLATES_DIR, build_templates

# Real API clients send versioned URLs — Meta's ``/v22.0/...``, TikTok's
# ``/v2/...``. The version is purely cosmetic for our purposes; strip it so
# route handlers can match on the clean path.
API_VERSION_RE = re.compile(r"^/v\d+(\.\d+)?(/|$)")

PKG = Path(__file__).parent
templates = build_templates()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Open the database and (in dev) mount the hot-reload watcher."""
    settings = get_settings()
    _app.state.db = Database(settings.database_url)

    try:
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
    finally:
        _app.state.db.close()


def create_app() -> FastAPI:
    """Build and return the posthole FastAPI application."""
    settings = get_settings()

    configure_logging(
        service="posthole",
        env=settings.environment,
        log_format=settings.log_format,
        log_level=settings.log_level,
    )

    app = FastAPI(
        title="posthole",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    install_correlation_middleware(app)

    @app.middleware("http")
    async def strip_api_version(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Strip ``/v22.0/...`` prefixes so platform routes see clean paths."""
        if API_VERSION_RE.match(request.url.path):
            request.scope["path"] = re.sub(r"^/v[^/]+", "", request.url.path) or "/"
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=PKG / "static"), name="static")

    # Order matters: UI routes first (so /, /accounts, /scenarios, /settings
    # win literal matches), then system (/_health), THEN platform routers —
    # those mount single-segment wildcards (IG's ``GET /{container_id}``) at
    # root that would otherwise swallow admin paths.
    #
    # Platform router contract (enforced by ordering, not by code):
    # 1. Platform routers MAY mount single-segment wildcards at the root
    #    (e.g. ``GET /{container_id}``) because real API paths look like that.
    # 2. Any new UI/admin route owned by ``pages`` or ``system`` MUST be
    #    a literal path so FastAPI's first-match resolution picks it up
    #    before falling through to a platform wildcard.
    # 3. Two platforms mounting overlapping wildcards (e.g. both grabbing
    #    ``GET /{id}``) will collide silently — the first registered wins.
    #    If a future platform needs that shape, namespace it (mount under
    #    ``/<platform>-containers/{id}`` etc.) rather than reordering.
    app.include_router(pages.build_router(templates))
    app.include_router(system.router)

    for plat in PLATFORMS:
        plat.install_exception_handlers(app)
        app.include_router(plat.build_router(templates))

    return app


app = create_app()
