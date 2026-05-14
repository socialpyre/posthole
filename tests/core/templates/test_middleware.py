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

from posthole.core.templates.middleware import TemplateContextMiddleware
from posthole.main import app as real_app

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from fastapi.responses import Response


async def test_middleware_is_registered_on_real_app() -> None:
    """Regression guard: removing the wiring in main.py shouldn't pass tests silently."""
    registered_classes = [m.cls for m in real_app.user_middleware]
    assert TemplateContextMiddleware in registered_classes, (
        "TemplateContextMiddleware not registered on the real app — check main.create_app() wiring."
    )


async def test_middleware_passthrough_does_not_break_request_cycle() -> None:
    """The real (empty) middleware passes requests through unchanged."""
    stub_app = FastAPI()
    stub_app.add_middleware(TemplateContextMiddleware)

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

    Monkeypatches :meth:`TemplateContextMiddleware.dispatch` to stamp a
    known value, mounts the middleware on a stub app, and asserts the
    handler sees the value via ``request.state``.
    """

    async def stamp(
        _self: TemplateContextMiddleware,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.probe = "stamped-by-middleware"
        return await call_next(request)

    monkeypatch.setattr(TemplateContextMiddleware, "dispatch", stamp)

    stub_app = FastAPI()
    stub_app.add_middleware(TemplateContextMiddleware)

    @stub_app.get("/probe")
    async def probe(request: Request) -> dict[str, str]:
        return {"probe": request.state.probe}

    transport = httpx.ASGITransport(app=stub_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/probe")

    assert response.status_code == 200
    assert response.json() == {"probe": "stamped-by-middleware"}
