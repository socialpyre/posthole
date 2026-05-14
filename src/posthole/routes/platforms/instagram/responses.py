"""Meta-shaped JSON envelopes + OpenAPI models for Instagram routes.

Real Meta returns JSON like
``{"error": {"message": "...", "type": "OAuthException", "code": 190, ...}}``
on every non-2xx response. Real clients parse that shape, so the mock must
match exactly.

``meta_error()`` is the low-level renderer used by ``MetaAPIError.to_response()``.
``MetaErrorResponse`` is the Pydantic model FastAPI uses to document the
shape in OpenAPI / Swagger UI — pass ``META_ERROR_RESPONSES`` as ``responses=``
on an ``APIRouter`` to get 400/401/404 docs for every route under it.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class MetaErrorBody(BaseModel):
    """The inner ``error`` object Meta returns on every non-2xx response.

    Note: ``error_subcode`` is OMITTED from the wire payload when ``None``
    (see :func:`meta_error`). The OpenAPI schema documents it as nullable
    because Pydantic can't easily express "absent on null" — clients should
    treat a missing key the same as ``null``.
    """

    message: str
    type: str
    code: int
    error_subcode: int | None = Field(
        default=None,
        description="Meta sub-error code; absent from the wire when null.",
    )


class MetaErrorResponse(BaseModel):
    """Wrapper shape ``{"error": {...}}`` — what FastAPI documents as 4xx body."""

    error: MetaErrorBody


META_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": MetaErrorResponse, "description": "Bad request"},
    401: {"model": MetaErrorResponse, "description": "Unauthorized"},
    404: {"model": MetaErrorResponse, "description": "Not found"},
}


def meta_error(
    *,
    status: int,
    message: str,
    error_type: str = "GraphMethodException",
    code: int = 0,
    error_subcode: int | None = None,
) -> JSONResponse:
    """Return a Meta-shaped error JSON response."""
    payload: dict[str, Any] = {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
        },
    }
    if error_subcode is not None:
        payload["error"]["error_subcode"] = error_subcode
    return JSONResponse(status_code=status, content=payload)
