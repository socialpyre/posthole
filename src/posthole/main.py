"""FastAPI application factory for posthole."""

from pathlib import Path

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from posthole import __version__
from posthole.core.config import get_settings
from posthole.core.csrf import CSRFOriginMiddleware
from posthole.core.exceptions import NotFoundError, handle_not_found
from posthole.core.lifecycle import lifespan
from posthole.core.logging import configure_logging
from posthole.core.logging.middleware import CORRELATION_KWARGS
from posthole.core.templates import TemplateContextMiddleware
from posthole.routes import router
from posthole.routes.pages.posts.exceptions import PostNotFoundError
from posthole.routes.pages.posts.handlers import handle_post_not_found
from posthole.routes.platforms import PLATFORMS, VersionStripMiddleware

PKG = Path(__file__).parent


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

    # Starlette wraps in reverse: CSRF runs first, then version-strip, etc.
    app.add_middleware(TemplateContextMiddleware)
    app.add_middleware(CorrelationIdMiddleware, **CORRELATION_KWARGS)
    app.add_middleware(VersionStripMiddleware)
    app.add_middleware(CSRFOriginMiddleware)

    app.mount("/static", StaticFiles(directory=PKG / "static"), name="static")

    app.add_exception_handler(NotFoundError, handle_not_found)
    app.add_exception_handler(PostNotFoundError, handle_post_not_found)
    for plat in PLATFORMS:
        app.add_exception_handler(plat.error_type, plat.error_handler)

    app.include_router(router)

    return app


app = create_app()
