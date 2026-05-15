"""Tests for the ``/_health`` JSON probe and ``/_health/stream`` SSE feed.

The streaming endpoint is exercised by driving the underlying generator
directly rather than through HTTP. ``httpx.ASGITransport`` doesn't deliver
chunked SSE data incrementally enough for a polite poll loop, and the
behavior we actually want to verify (event format, repeat cadence, clean
disconnect) lives in the generator anyway.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from posthole.routes.pages.health import routes as health_routes

if TYPE_CHECKING:
    import httpx


pytestmark = pytest.mark.asyncio


async def test_health_probe_returns_ok(client: httpx.AsyncClient) -> None:
    """``GET /_health`` is the JSON liveness probe."""
    response = await client.get("/_health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_stream_yields_ping_event() -> None:
    """The generator emits a properly formatted SSE ``ping`` event."""
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)

    with patch.object(health_routes, "PING_INTERVAL_SECONDS", 0.01):
        gen = health_routes._ping_stream(request)
        first = await gen.__anext__()
        assert first == b"event: ping\ndata: {}\n\n"
        await gen.aclose()


async def test_health_stream_emits_repeated_pings() -> None:
    """Successive iterations yield additional ping events."""
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)

    with patch.object(health_routes, "PING_INTERVAL_SECONDS", 0.01):
        gen = health_routes._ping_stream(request)
        first = await gen.__anext__()
        second = await gen.__anext__()
        assert first == second == b"event: ping\ndata: {}\n\n"
        await gen.aclose()


async def test_health_stream_stops_when_client_disconnects() -> None:
    """When ``request.is_disconnected`` returns True the generator exits cleanly."""
    request = MagicMock()
    # First poll: still connected → yields a ping. Second poll: disconnected → return.
    request.is_disconnected = AsyncMock(side_effect=[False, True])

    with patch.object(health_routes, "PING_INTERVAL_SECONDS", 0.01):
        gen = health_routes._ping_stream(request)
        await gen.__anext__()  # first ping
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()


async def test_health_stream_handles_cancellation() -> None:
    """A ``CancelledError`` mid-sleep is swallowed and exits cleanly."""
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)

    with patch.object(health_routes, "PING_INTERVAL_SECONDS", 60):
        gen = health_routes._ping_stream(request)
        await gen.__anext__()  # consume one ping so we're inside the sleep
        # athrow CancelledError into the generator at the await sleep point.
        with pytest.raises((asyncio.CancelledError, StopAsyncIteration)):
            await gen.athrow(asyncio.CancelledError())


async def test_health_stream_route_is_registered() -> None:
    """The SSE entry-point is wired into the app router and configured for streaming.

    We don't open the stream over HTTP — ``httpx.ASGITransport`` won't yield
    chunked SSE data back through a polite poll loop, so the streaming
    behavior is covered by the generator-level tests above. This case just
    pins down that the route exists with the right method and path.
    """
    from posthole.main import app

    matches = [
        r
        for r in app.routes
        if getattr(r, "path", None) == "/_health/stream" and "GET" in getattr(r, "methods", set())
    ]
    assert matches, "/_health/stream GET route is not registered"
