"""Health routes: ``/_health`` JSON probe + ``/_health/stream`` SSE heartbeat."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

PING_INTERVAL_SECONDS = 10.0

router = APIRouter()


@router.get("/_health")
async def health() -> dict[str, str]:
    """Liveness probe used by Docker and load balancers."""
    return {"status": "ok"}


@router.get("/_health/stream")
async def health_stream(request: Request) -> StreamingResponse:
    """Server-sent events heartbeat the topbar liveness badge subscribes to.

    Emits one ``ping`` event immediately on connect (so the client confirms
    liveness without waiting a full interval), then one every
    :data:`PING_INTERVAL_SECONDS`. Closes cleanly when the client
    disconnects.
    """
    return StreamingResponse(
        _ping_stream(request),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so the initial ping reaches the client
            # immediately instead of waiting for the response to fill a chunk.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _ping_stream(request: Request) -> AsyncGenerator[bytes, None]:
    """Yield an SSE ``ping`` event every :data:`PING_INTERVAL_SECONDS`."""
    try:
        while True:
            if await request.is_disconnected():
                return
            yield b"event: ping\ndata: {}\n\n"
            await asyncio.sleep(PING_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        # Client closed the connection — Starlette propagates cancellation
        # to the generator. Exit cleanly without re-raising.
        return
