"""Correlation middleware — populates the ``request_id`` contextvar."""

from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

HEADER = "X-Request-ID"


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


# ``Mapping[str, Any]`` (rather than ``Mapping[str, object]``) so the
# heterogeneous values (str, bool, two callables) survive ``**`` unpacking
# at the call site without each kwarg getting flagged as the wrong type.
CORRELATION_KWARGS: Mapping[str, Any] = MappingProxyType(
    {
        "header_name": HEADER,
        "update_request_header": True,
        "generator": lambda: str(uuid.uuid4()),
        "validator": validate_incoming,
    },
)

__all__ = ["CORRELATION_KWARGS", "HEADER", "validate_incoming"]
