"""TikTok-shaped JSON envelopes + OpenAPI models for TikTok routes.

TikTok wraps every response (success AND failure) as:

    {"data": {...}, "error": {"code": "ok|<err_code>", "message": "...", "log_id": "..."}}

``error.code == "ok"`` is the success sentinel — both keys are always
present. This is structurally different from Meta's envelope (which omits
``error`` on success and has no ``data`` sibling), so we deliberately do
**not** share helpers with ``platforms/instagram/responses.py``.

The token-exchange endpoint (`POST /v2/oauth/token/`) is the one exception:
TikTok returns a flat OAuth2-shaped body there with no wrapping envelope.
Use plain ``dict`` returns for that handler.

``tiktok_error()`` is the low-level renderer used by
``TikTokAPIError.to_response()``. ``TikTokErrorResponse`` documents the
dual-envelope shape in OpenAPI; pass ``TIKTOK_ERROR_RESPONSES`` as
``responses=`` on an ``APIRouter`` for 400/401/404 docs.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


def _gen_log_id() -> str:
    """Mint a log_id that visually resembles TikTok's real ones (20-ish digits)."""
    return secrets.token_hex(10)


class TikTokErrorBody(BaseModel):
    """The inner ``error`` object TikTok always returns (``code='ok'`` = success)."""

    code: str
    message: str
    log_id: str


class TikTokErrorResponse(BaseModel):
    """Dual-envelope shape ``{"data": {}, "error": {...}}`` for non-2xx responses."""

    data: dict[str, Any] = Field(default_factory=dict)
    error: TikTokErrorBody


TIKTOK_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": TikTokErrorResponse, "description": "Bad request"},
    401: {"model": TikTokErrorResponse, "description": "Unauthorized"},
    404: {"model": TikTokErrorResponse, "description": "Not found"},
}


def tiktok_envelope(
    data: dict[str, Any] | None = None,
    *,
    code: str = "ok",
    message: str = "",
    log_id: str | None = None,
) -> dict[str, Any]:
    """Build the standard TikTok response envelope. ``code='ok'`` signals success."""
    return {
        "data": data or {},
        "error": {
            "code": code,
            "message": message,
            "log_id": log_id or _gen_log_id(),
        },
    }


def tiktok_error(
    *,
    http_status: int,
    code: str,
    message: str,
) -> JSONResponse:
    """Return a TikTok dual-envelope error response."""
    return JSONResponse(
        status_code=http_status,
        content=tiktok_envelope({}, code=code, message=message),
    )
