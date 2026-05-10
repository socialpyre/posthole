"""Tests for HTML page routes."""

import httpx
import pytest


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/", "No posts yet"),
        ("/accounts", "No accounts"),
        ("/scenarios", "All scenarios off"),
        ("/settings", "Settings"),
    ],
)
async def test_view_renders(client: httpx.AsyncClient, path: str, marker: str) -> None:
    """Each page route returns 200 and contains its empty-state copy."""
    response = await client.get(path)

    assert response.status_code == 200
    assert marker in response.text


async def test_health_returns_ok(client: httpx.AsyncClient) -> None:
    """``/_health`` returns 200 with ``{"status": "ok"}``."""
    response = await client.get("/_health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
