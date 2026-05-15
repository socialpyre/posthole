"""CSRF guard: reject unsafe-method requests whose Origin doesn't match Host.

The threat model is a rogue same-machine page hitting localhost. Browsers
always send ``Origin`` on cross-origin writes; ``curl`` / IDE tools omit
it. We block mismatched origins and allow missing ones.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFOriginMiddleware:
    """Pure-ASGI middleware: blocks state-changing requests on Origin mismatch."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Guard HTTP scope only; WebSocket upgrades pass through."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope["method"]
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        headers = _header_dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode("latin-1")
        origin = headers.get(b"origin")
        referer = headers.get(b"referer")

        if not host:
            await _send_csrf_error(send, "missing host")
            return

        if origin is not None:
            if not _host_matches(origin.decode("latin-1"), host):
                await _send_csrf_error(send, "origin mismatch")
                return
        elif referer is not None and not _host_matches(referer.decode("latin-1"), host):
            await _send_csrf_error(send, "referer mismatch")
            return

        await self.app(scope, receive, send)


def _header_dict(raw: list[tuple[bytes, bytes]]) -> dict[bytes, bytes]:
    """Last-value-wins index of ASGI raw headers, keyed by lowercase name."""
    out: dict[bytes, bytes] = {}
    for name, value in raw:
        out[name.lower()] = value
    return out


def _host_matches(url: str, host: str) -> bool:
    """``True`` if ``url``'s netloc matches ``host``; empty/unparseable returns ``False``."""
    parsed = urlsplit(url)
    if not parsed.netloc:
        return False
    return parsed.netloc.lower() == host.lower()


async def _send_csrf_error(send: Send, reason: str) -> None:
    """Emit a 403 text/plain response naming the reject reason."""
    body = f"CSRF: {reason}".encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


__all__ = ["CSRFOriginMiddleware"]
