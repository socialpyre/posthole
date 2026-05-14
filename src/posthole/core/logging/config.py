"""Configure structlog for posthole.

``configure_logging`` is safe to call repeatedly. We deliberately do not touch
the stdlib root logger: uvicorn / fastapi-cli own that output and
reconfiguring it duplicates every startup line.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

from posthole.core.logging.processors import (
    add_correlation_id,
    add_service_metadata,
    redact_sensitive,
    set_metadata,
)
from posthole.core.logging.terminal import console_renderer

NOISY_WS_MESSAGES = frozenset({"connection open", "connection closed"})


def configure_logging(
    service: str = "posthole",
    env: str = "local",
    *,
    log_format: str = "console",
    log_level: str = "DEBUG",
) -> None:
    """Configure structlog with the posthole processor chain.

    Args:
        service: Stamped onto every log line as ``service``.
        env: Stamped as ``env``. Conventionally "local" or "prod".
        log_format: ``"console"`` for pretty colored output, anything else
            (``"json"``) for newline-delimited JSON.
        log_level: Standard Python log level name. Filters structlog output via
            ``make_filtering_bound_logger``; the stdlib root logger is untouched.
    """
    set_metadata(service, env)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_service_metadata,
        add_correlation_id,
        redact_sensitive,
        structlog.processors.add_log_level,
    ]

    if log_format == "console":
        processors.append(console_renderer)
    else:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        cache_logger_on_first_use=True,
    )

    uvicorn_error = logging.getLogger("uvicorn.error")
    if drop_websocket_lifecycle not in uvicorn_error.filters:
        uvicorn_error.addFilter(drop_websocket_lifecycle)


def drop_websocket_lifecycle(record: logging.LogRecord) -> bool:
    """Drop the bare ``connection open`` / ``connection closed`` framing lines.

    Uvicorn passes ``logging.getLogger("uvicorn.error")`` into the websockets
    library, so those messages surface there. The preceding
    ``"WebSocket /path"`` access-log line already names the connection.
    """
    return record.getMessage() not in NOISY_WS_MESSAGES


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger, optionally namespaced by ``name``."""
    return structlog.get_logger(name) if name else structlog.get_logger()


__all__ = ["configure_logging", "get_logger"]
