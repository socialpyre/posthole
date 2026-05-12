"""Correlation middleware — populates the ``request_id`` contextvar.

Wraps ``asgi-correlation-id``'s :class:`CorrelationIdMiddleware` with posthole
conventions: header is ``X-Request-ID``, incoming values must parse as a UUID
(else discarded and a fresh UUID4 is minted), and the value is mirrored back
on the response. The processor chain reads the resulting contextvar and stamps
``request_id`` onto every log line.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from asgi_correlation_id import CorrelationIdMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

HEADER = "X-Request-ID"


def install_correlation_middleware(app: FastAPI) -> None:
    """Install correlation middleware.

    Starlette adds middleware in reverse registration order, so if other
    middlewares are added later, call this **first** to keep it outermost.
    """
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=HEADER,
        update_request_header=True,
        generator=lambda: str(uuid.uuid4()),
        validator=validate_incoming,
    )


def validate_incoming(header_value: str | None) -> bool:
    """Accept incoming correlation IDs only if they parse as a UUID.

    Prevents arbitrary client strings (potentially with newlines, ANSI escapes,
    or other log-shaping characters) from becoming the request_id stamped on
    every log line. Anything malformed or empty is rejected and
    ``CorrelationIdMiddleware`` falls back to its ``generator``.
    """
    if not header_value:
        return False

    try:
        uuid.UUID(header_value)
    except (ValueError, AttributeError, TypeError):
        return False

    return True


__all__ = ["install_correlation_middleware"]
