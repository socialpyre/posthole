"""Tests for HTML page routes."""

import httpx
import pytest

from posthole.db import Database, accounts, posts


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/posts", "No posts yet"),
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


async def test_post_detail_unknown_id_returns_404(client: httpx.AsyncClient) -> None:
    """``/posts/{id}`` for an unknown id returns 404 via the ``NotFoundError`` handler.

    The response body is the inbox shell with ``not_found=True``, so a
    Turbo Frame click that lands on a deleted post cleanly swaps the
    detail pane without losing the list.
    """
    response = await client.get("/posts/anything")

    assert response.status_code == 404


async def test_root_redirects_to_posts(client: httpx.AsyncClient) -> None:
    """``GET /`` 307s to ``/posts`` — the inbox lives there now."""
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/posts"


@pytest.mark.parametrize(
    ("path", "expected_href"),
    [
        ("/posts", "/posts"),
        ("/posts/anything", "/posts"),
        ("/accounts", "/accounts"),
        ("/scenarios", "/scenarios"),
        ("/settings", "/settings"),
    ],
)
async def test_sidenav_highlights_current_section(
    client: httpx.AsyncClient, path: str, expected_href: str
) -> None:
    """Sidenav marks the section nav link ``aria-current="page"``.

    Hierarchical match: ``/posts/anything`` (a 404 sub-page) still
    highlights ``/posts``.
    """
    response = await client.get(path)

    # Search for the anchor whose href matches the expected section, with
    # aria-current="page" anywhere in its attributes. The template wraps
    # attributes across lines, so a simple substring check would be brittle.
    fragment = f'href="{expected_href}"'
    assert fragment in response.text
    # The aria-current attr lands BEFORE the class= attr in the rendered
    # markup. Find the anchor block and confirm aria-current is inside it.
    anchor_start = response.text.find(fragment)
    anchor_end = response.text.find("</a>", anchor_start)
    anchor_block = response.text[anchor_start:anchor_end]
    assert 'aria-current="page"' in anchor_block


@pytest.mark.parametrize(
    ("path", "has_search"),
    [
        ("/posts", True),
        ("/posts/anything", True),
        ("/accounts", False),
        ("/scenarios", False),
        ("/settings", False),
    ],
)
async def test_search_input_scoped_to_posts(
    client: httpx.AsyncClient, path: str, has_search: bool
) -> None:
    """The topbar search input renders only on posts routes."""
    response = await client.get(path)

    assert ('id="topbar-search"' in response.text) is has_search


async def test_search_filters_inbox(client: httpx.AsyncClient, db: Database) -> None:
    """``?q=`` filters the inbox list by caption / account_id / handle."""
    account = accounts.get(db, "178414000000001")  # seeded via fixture migrations
    assert account is not None, "expected seeded account 178414000000001"

    matching = posts.create(
        db, platform="instagram", account_id=account.id, caption="golden hour shot"
    )
    other = posts.create(
        db, platform="instagram", account_id=account.id, caption="late-night latte"
    )

    response = await client.get("/posts?q=golden")

    assert response.status_code == 200
    assert matching.id in response.text
    assert other.id not in response.text
    # The input echoes the query back.
    assert 'value="golden"' in response.text


async def test_search_no_match_renders_empty_state(client: httpx.AsyncClient) -> None:
    """``?q=`` with no matches renders the empty-state copy."""
    response = await client.get("/posts?q=zzzzzz_no_match")

    assert response.status_code == 200
    assert "No posts yet" in response.text


async def test_search_persists_on_detail(client: httpx.AsyncClient, db: Database) -> None:
    """``/posts/{id}?q=foo`` keeps the list filtered AND echoes q into the input."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="golden hour")

    response = await client.get(f"/posts/{target.id}?q=golden")

    assert response.status_code == 200
    assert 'value="golden"' in response.text
    # Row link preserves the query so clicking elsewhere keeps the filter.
    assert f"/posts/{target.id}?q=golden" in response.text
