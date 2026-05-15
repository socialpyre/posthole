"""Tests for HTML page routes."""

import httpx
import pytest

from posthole.db import Database, accounts, posts


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        # /posts has the demo carousel seeded by migration 0003, so the
        # empty-state copy no longer applies; assert the inbox shell instead.
        ("/posts", 'id="post-detail"'),
        ("/accounts", "No accounts"),
        ("/scenarios", "All scenarios off"),
        ("/settings", "Settings"),
    ],
)
async def test_view_renders(client: httpx.AsyncClient, path: str, marker: str) -> None:
    """Each page route returns 200 and contains its expected marker."""
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
    """``?q=`` with no matches renders the filtered-empty copy + Clear filters."""
    response = await client.get("/posts?q=zzzzzz_no_match")

    assert response.status_code == 200
    assert "No matching posts" in response.text
    assert "Clear filters" in response.text


async def test_platform_filter_scopes_list(client: httpx.AsyncClient, db: Database) -> None:
    """``?platform=instagram`` shows only IG rows; ``?platform=tiktok`` only TT rows."""
    ig_account = accounts.get(db, "178414000000001")
    tt_account = accounts.get_by_username(db, "test_creator")
    assert ig_account is not None
    assert tt_account is not None
    ig = posts.create(db, platform="instagram", account_id=ig_account.id, caption="ig only")
    tt = posts.create(db, platform="tiktok", account_id=tt_account.id, caption="tt only")

    ig_response = await client.get("/posts?platform=instagram")
    assert ig_response.status_code == 200
    assert ig.id in ig_response.text
    assert tt.id not in ig_response.text

    tt_response = await client.get("/posts?platform=tiktok")
    assert tt_response.status_code == 200
    assert tt.id in tt_response.text
    assert ig.id not in tt_response.text


async def test_platform_filter_garbage_falls_back_to_all(
    client: httpx.AsyncClient, db: Database
) -> None:
    """``?platform=GARBAGE`` normalizes to None — list shows everything."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    ig = posts.create(db, platform="instagram", account_id=account.id, caption="hello")

    response = await client.get("/posts?platform=GARBAGE")
    assert response.status_code == 200
    assert ig.id in response.text


async def test_status_filter_scopes_list(client: httpx.AsyncClient, db: Database) -> None:
    """``?status=published`` and ``?status=failed`` each scope the list to their status."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    pending = posts.create(db, platform="instagram", account_id=account.id, caption="pending")
    published = posts.create(db, platform="instagram", account_id=account.id, caption="published")
    posts.mark_published(db, published.id)
    failed = posts.create(db, platform="instagram", account_id=account.id, caption="failed")
    posts.mark_failed(db, failed.id, "explode")

    pub_response = await client.get("/posts?status=published")
    assert pub_response.status_code == 200
    assert published.id in pub_response.text
    assert pending.id not in pub_response.text
    assert failed.id not in pub_response.text

    fail_response = await client.get("/posts?status=failed")
    assert fail_response.status_code == 200
    assert failed.id in fail_response.text
    assert published.id not in fail_response.text


async def test_platform_and_status_filters_compose(client: httpx.AsyncClient, db: Database) -> None:
    """``?platform=tiktok&status=published`` keeps only the rows matching both axes."""
    ig_account = accounts.get(db, "178414000000001")
    tt_account = accounts.get_by_username(db, "test_creator")
    assert ig_account is not None
    assert tt_account is not None

    ig_published = posts.create(
        db, platform="instagram", account_id=ig_account.id, caption="ig pub"
    )
    posts.mark_published(db, ig_published.id)
    tt_published = posts.create(db, platform="tiktok", account_id=tt_account.id, caption="tt pub")
    posts.mark_published(db, tt_published.id)
    tt_pending = posts.create(db, platform="tiktok", account_id=tt_account.id, caption="tt pending")

    response = await client.get("/posts?platform=tiktok&status=published")
    assert response.status_code == 200
    assert tt_published.id in response.text
    assert tt_pending.id not in response.text
    assert ig_published.id not in response.text


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


async def test_post_detail_renders_phone_frame_with_image(
    client: httpx.AsyncClient, db: Database
) -> None:
    """A single-image post renders an <img> inside the device-screen."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(
        db,
        platform="instagram",
        account_id=account.id,
        caption="hello",
        media_url="https://picsum.photos/seed/test-img/1080/1080",
        media_type="IMAGE",
    )

    response = await client.get(f"/posts/{target.id}")

    assert response.status_code == 200
    assert 'data-controller="phone"' in response.text
    assert "device-iphone-14-pro" in response.text
    assert "https://picsum.photos/seed/test-img/1080/1080" in response.text


async def test_post_detail_renders_carousel(client: httpx.AsyncClient) -> None:
    """The seeded demo carousel renders 3 slides + counter + carousel controller."""
    response = await client.get("/posts/demo-carousel-0001")

    assert response.status_code == 200
    assert 'data-controller="carousel"' in response.text
    assert response.text.count('data-carousel-target="slide"') == 3
    assert "1/3" in response.text


async def test_post_detail_renders_video_poster(client: httpx.AsyncClient, db: Database) -> None:
    """A VIDEO-typed single post renders the play-poster gradient (no <img>)."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(
        db,
        platform="tiktok",
        account_id=account.id,
        media_url="https://video.example/clip.mp4",
        media_type="VIDEO",
    )

    response = await client.get(f"/posts/{target.id}")

    assert response.status_code == 200
    # The video branch emits no <img> for the media URL; it renders a
    # gradient + play icon. Confirm the URL isn't in the visible markup
    # the way the image branch would surface it.
    assert 'src="https://video.example/clip.mp4"' not in response.text
    assert "from-gray-700" in response.text  # gradient class used by the video poster


async def test_post_detail_view_metadata_activates_metadata_tab(
    client: httpx.AsyncClient, db: Database
) -> None:
    """``?view=metadata`` flips the server-rendered active tab + panel."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="x")

    response = await client.get(f"/posts/{target.id}?view=metadata")

    assert response.status_code == 200
    # Metadata tab is selected, Preview tab isn't.
    metadata_tab_start = response.text.find('id="tab-metadata"')
    metadata_tab_block = response.text[metadata_tab_start : metadata_tab_start + 400]
    assert 'aria-selected="true"' in metadata_tab_block
    preview_tab_start = response.text.find('id="tab-preview"')
    preview_tab_block = response.text[preview_tab_start : preview_tab_start + 400]
    assert 'aria-selected="false"' in preview_tab_block
    # Preview panel is the one server-rendered hidden now.
    preview_panel_start = response.text.find('id="panel-preview"')
    preview_panel_block = response.text[preview_panel_start : preview_panel_start + 400]
    assert "hidden" in preview_panel_block


async def test_post_detail_view_preview_matches_no_param(
    client: httpx.AsyncClient, db: Database
) -> None:
    """``?view=preview`` is the default; behaves the same as no param."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="x")

    explicit = await client.get(f"/posts/{target.id}?view=preview")
    implicit = await client.get(f"/posts/{target.id}")

    assert explicit.status_code == 200
    assert implicit.status_code == 200
    preview_tab_explicit = explicit.text.find('id="tab-preview"')
    preview_tab_implicit = implicit.text.find('id="tab-preview"')
    assert (
        'aria-selected="true"' in explicit.text[preview_tab_explicit : preview_tab_explicit + 400]
    )
    assert (
        'aria-selected="true"' in implicit.text[preview_tab_implicit : preview_tab_implicit + 400]
    )


async def test_post_detail_view_garbage_falls_back_to_preview(
    client: httpx.AsyncClient, db: Database
) -> None:
    """Unknown ``view`` value renders Preview, not a 4xx — this is view UI."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="x")

    response = await client.get(f"/posts/{target.id}?view=garbage")

    assert response.status_code == 200
    preview_tab_start = response.text.find('id="tab-preview"')
    assert 'aria-selected="true"' in response.text[preview_tab_start : preview_tab_start + 400]


async def test_post_detail_q_and_view_coexist(client: httpx.AsyncClient, db: Database) -> None:
    """``?q=`` and ``?view=`` are independent: filter stays AND metadata activates."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="golden hour")

    response = await client.get(f"/posts/{target.id}?q=golden&view=metadata")

    assert response.status_code == 200
    assert 'value="golden"' in response.text  # search input echo
    metadata_tab_start = response.text.find('id="tab-metadata"')
    assert 'aria-selected="true"' in response.text[metadata_tab_start : metadata_tab_start + 400]


async def test_post_detail_404_accepts_view_param(client: httpx.AsyncClient) -> None:
    """The 404 path threads ``view`` through context without crashing.

    The not-found pane doesn't render tabs (only the detail pane does), so
    there's no user-visible difference per ``view`` here. This guards
    against a regression where the exception handler doesn't accept
    ``view`` and 500s on a stale URL — assert the not-found copy actually
    rendered so a future "swallow the exception and serve empty" bug is
    caught too.
    """
    response = await client.get("/posts/does-not-exist?view=metadata")

    assert response.status_code == 404
    assert "Post not found" in response.text


async def test_post_detail_emits_controller_contract_attrs(
    client: httpx.AsyncClient, db: Database
) -> None:
    """The rendered tabs markup carries the exact data-* attrs the Stimulus
    controller reads.

    The macros and the controller live in different files in different
    languages; nothing else asserts they agree on attribute names.
    Renaming either side without updating this test would catch the
    drift here.
    """
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="x")

    response = await client.get(f"/posts/{target.id}")

    assert response.status_code == 200
    # Controller mount + param wiring.
    assert 'data-controller="tabs"' in response.text
    assert 'data-tabs-param-value="view"' in response.text
    assert 'data-tabs-default-panel-value="preview"' in response.text
    # Targets the controller queries by name.
    assert 'data-tabs-target="tab"' in response.text
    assert 'data-tabs-target="panel"' in response.text
    # Per-tab/panel key used by `select`/`go` to find the matching panel.
    assert 'data-tabs-key="preview"' in response.text
    assert 'data-tabs-key="metadata"' in response.text
    assert 'data-panel="preview"' in response.text
    assert 'data-panel="metadata"' in response.text
    # Click + keyboard actions bound on the tabs.
    assert 'data-action="click->tabs#select keydown->tabs#keydown"' in response.text


async def test_post_detail_renders_tabs_with_metadata_hidden(
    client: httpx.AsyncClient, db: Database
) -> None:
    """Detail pane renders Preview + Metadata tabs; metadata panel starts hidden."""
    account = accounts.get(db, "178414000000001")
    assert account is not None
    target = posts.create(db, platform="instagram", account_id=account.id, caption="x")

    response = await client.get(f"/posts/{target.id}")

    assert response.status_code == 200
    assert 'id="tab-preview"' in response.text
    assert 'id="tab-metadata"' in response.text
    assert 'aria-selected="true"' in response.text
    # The metadata panel is server-rendered hidden so a no-JS reader still
    # sees the phone-frame preview.
    metadata_start = response.text.find('id="panel-metadata"')
    assert metadata_start != -1
    metadata_block = response.text[metadata_start : metadata_start + 200]
    assert "hidden" in metadata_block
