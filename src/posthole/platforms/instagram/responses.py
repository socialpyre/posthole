"""Meta-shaped error envelopes for Instagram routes.

Real Meta returns JSON like
``{"error": {"message": "...", "type": "OAuthException", "code": 190, ...}}``
on every non-2xx response. Real clients parse that shape, so the mock must
match exactly.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


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
