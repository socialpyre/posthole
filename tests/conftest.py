"""Shared pytest fixtures for the posthole test suite."""

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio

from posthole.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """Yield an httpx ``AsyncClient`` bound to the in-process ASGI app."""
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
