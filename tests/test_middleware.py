"""Tests for the per-request template-context middleware.

The middleware itself is currently a pass-through; these tests guard the
contract for when per-request values land (request_id, current account,
theme override, etc.) by exercising the stamp-and-read pattern via a
small stub FastAPI app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from fastapi import FastAPI, Request

from posthole.main import app as real_app
from posthole.web import middleware as mw

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from fastapi.responses import Response


async def test_middleware_is_registered_on_real_app() -> None:
    """Regression guard: removing the wiring in main.py shouldn't pass tests silently."""
    registered = [getattr(m, "kwargs", {}).get("dispatch") for m in real_app.user_middleware]
    assert mw._populate_request_state in registered, (
        "install_template_context_middleware not registered on the real app — "
        "check main.create_app() wiring."
    )


async def test_middleware_passthrough_does_not_break_request_cycle() -> None:
    """The real (empty) middleware passes requests through unchanged."""
    stub_app = FastAPI()
    mw.install_template_context_middleware(stub_app)

    @stub_app.get("/echo")
    async def echo() -> dict[str, str]:
        return {"ok": "true"}

    transport = httpx.ASGITransport(app=stub_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/echo")

    assert response.status_code == 200
    assert response.json() == {"ok": "true"}


async def test_request_state_populated_in_middleware_visible_in_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stamp-and-read pattern future per-request values will use.

    Patches ``_populate_request_state`` to stamp a known value, mounts the
    middleware on a stub app, and asserts the handler sees the value via
    ``request.state``.
    """

    async def stamp(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.probe = "stamped-by-middleware"
        return await call_next(request)

    monkeypatch.setattr(mw, "_populate_request_state", stamp)

    stub_app = FastAPI()
    mw.install_template_context_middleware(stub_app)

    @stub_app.get("/probe")
    async def probe(request: Request) -> dict[str, str]:
        return {"probe": request.state.probe}

    transport = httpx.ASGITransport(app=stub_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/probe")

    assert response.status_code == 200
    assert response.json() == {"probe": "stamped-by-middleware"}
