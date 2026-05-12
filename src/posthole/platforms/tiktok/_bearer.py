"""Bearer-token header parsing for TikTok handlers."""

from __future__ import annotations


def strip_bearer(authorization: str) -> str:
    """Pull the token out of an ``Authorization: Bearer …`` header (or '')."""
    if not authorization.lower().startswith("bearer "):
        return ""
    return authorization[len("bearer ") :].strip()
