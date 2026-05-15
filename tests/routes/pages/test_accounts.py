"""Tests for the ``/accounts`` view + create/delete handlers."""

import re
from datetime import UTC, datetime, timedelta

import httpx

from posthole.db import Database, accounts, oauth, posts


def _card_block(text: str, handle: str) -> str:
    """Return the slice of an /accounts response that belongs to one card.

    The grid renders one ``<article>`` per account, so finding the handle's
    occurrence and slicing to the next ``<article>`` (or to the next
    ``<dialog>`` for the trailing card) isolates that card's markup for
    targeted assertions without buying the regex weight of a real parser.
    """
    start = text.find(handle)
    end = text.find("<article", start + 1)
    if end == -1:
        end = text.find("<dialog", start + 1)
    return text[start : end if end != -1 else len(text)]


async def test_accounts_view_renders_seeded_cards(client: httpx.AsyncClient) -> None:
    """The grid renders one card per seeded account with handle + platform id."""
    response = await client.get("/accounts")

    assert response.status_code == 200
    assert "@test_studio" in response.text
    assert "@test_creator" in response.text
    assert "178414000000001" in response.text
    assert "tt-7000000000000000001" in response.text


async def test_accounts_filter_pills_scope_grid(client: httpx.AsyncClient) -> None:
    """``?platform=instagram`` hides TikTok cards; ``?platform=tiktok`` hides IG."""
    ig = await client.get("/accounts?platform=instagram")
    assert ig.status_code == 200
    assert "@test_studio" in ig.text
    assert "@test_creator" not in ig.text

    tt = await client.get("/accounts?platform=tiktok")
    assert tt.status_code == 200
    assert "@test_creator" in tt.text
    assert "@test_studio" not in tt.text


async def test_accounts_filter_garbage_falls_back_to_all(client: httpx.AsyncClient) -> None:
    """``?platform=GARBAGE`` normalizes to None — grid shows every platform."""
    response = await client.get("/accounts?platform=GARBAGE")

    assert response.status_code == 200
    assert "@test_studio" in response.text
    assert "@test_creator" in response.text


async def test_accounts_card_renders_intercepted_count(
    client: httpx.AsyncClient, db: Database
) -> None:
    """The card's intercepted stat reflects ``posts`` rows for that account.

    Guards against accidentally dropping the GROUP BY join — without it the
    card would show ``0`` regardless of capture history.
    """
    posts.create(db, platform="instagram", account_id="178414000000001", caption="alpha")
    posts.create(db, platform="instagram", account_id="178414000000001", caption="beta")

    response = await client.get("/accounts?platform=instagram")
    assert response.status_code == 200

    card = _card_block(response.text, "@test_studio")
    intercepted_idx = card.find("intercepted")
    stat_block = card[max(0, intercepted_idx - 200) : intercepted_idx]
    # 2 created here + 1 seeded demo carousel under test_studio (migration
    # 0003) = 3 captures minimum. The stat number sits on its own line
    # inside the surrounding ``<div>``.
    nums = re.findall(r"^\s*(\d+)\s*$", stat_block, flags=re.MULTILINE)
    assert nums, f"no intercepted stat number found in card block: {stat_block!r}"
    assert int(nums[-1]) >= 3


async def test_accounts_create_succeeds_with_303_and_inserts_row(
    client: httpx.AsyncClient, db: Database
) -> None:
    """Valid POST inserts the row and 303-redirects to the platform-filtered grid."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "newco.app",
            "display_name": "New Co",
            "account_type": "BUSINESS",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts?platform=instagram"

    inserted = accounts.get_by_username(db, "newco.app")
    assert inserted is not None
    assert inserted.platform == "instagram"
    assert inserted.account_type == "BUSINESS"


async def test_accounts_create_strips_leading_at_from_handle(
    client: httpx.AsyncClient, db: Database
) -> None:
    """``@`` prefix on the handle is silently stripped — the input shows ``@`` already."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "tiktok",
            "username": "@newcreator",
            "display_name": "New Creator",
            "account_type": "CREATOR_ACCOUNT",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert accounts.get_by_username(db, "newcreator") is not None


async def test_accounts_create_validation_rerenders_dialog_open(
    client: httpx.AsyncClient,
) -> None:
    """Blank fields → 400, page re-renders with the dialog open + per-field errors."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "",
            "display_name": "",
            "account_type": "BUSINESS",
        },
    )

    assert response.status_code == 400
    # The dialog markup carries the ``open`` attribute so the Stimulus
    # controller re-opens it as a modal on connect; the user sees their
    # errors without losing the form context.
    dialog_idx = response.text.find('id="new-account-dialog"')
    dialog_block = response.text[dialog_idx : dialog_idx + 400]
    assert " open" in dialog_block
    assert "Handle is required." in response.text
    assert "Display name is required." in response.text


async def test_accounts_create_rejects_duplicate_username(
    client: httpx.AsyncClient,
) -> None:
    """Re-submitting an existing handle on the same platform → 409 with inline error."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "test_studio",  # already seeded by migration 0001
            "display_name": "Imposter Studio",
            "account_type": "BUSINESS",
        },
    )

    assert response.status_code == 409
    assert "Handle already taken" in response.text


async def test_accounts_create_allows_same_handle_on_different_platform(
    client: httpx.AsyncClient,
) -> None:
    """``(platform, username)`` is the unique key — same handle on TikTok is fine."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "tiktok",
            "username": "test_studio",  # exists on Instagram, not TikTok
            "display_name": "Test Studio TT",
            "account_type": "BUSINESS_ACCOUNT",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


async def test_accounts_create_rejects_handle_with_leading_dot(
    client: httpx.AsyncClient,
) -> None:
    """A handle starting with ``.`` is rejected — IG/TT both reject it, and the
    constraint also keeps the value from ever rendering as ``.`` / ``..``."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": ".leading",
            "display_name": "Dot Leading",
            "account_type": "BUSINESS",
        },
    )

    assert response.status_code == 400
    assert "Handle can only contain" in response.text


async def test_accounts_create_rejects_handle_with_invalid_characters(
    client: httpx.AsyncClient,
) -> None:
    """Whitespace / punctuation outside ``A-Za-z0-9._`` is rejected at the validator."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "a b/c",
            "display_name": "Invalid",
            "account_type": "BUSINESS",
        },
    )

    assert response.status_code == 400
    assert "Handle can only contain" in response.text


async def test_accounts_create_rejects_type_mismatched_to_platform(
    client: httpx.AsyncClient,
) -> None:
    """Picking a TikTok ``account_type`` on an Instagram form is a 400, not an insert."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "wrongtype",
            "display_name": "Wrong Type",
            "account_type": "CREATOR_ACCOUNT",
        },
    )

    assert response.status_code == 400
    assert "Pick an account type for this platform." in response.text


async def test_accounts_edit_updates_row_and_redirects(
    client: httpx.AsyncClient, db: Database
) -> None:
    """Valid edit POST updates the row and 303-redirects to the platform-filtered grid."""
    seeded = accounts.get(db, "178414000000001")
    assert seeded is not None

    response = await client.post(
        f"/accounts/{seeded.id}/edit",
        data={
            "username": "renamed.studio",
            "display_name": "Renamed Studio",
            "account_type": "CREATOR",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts?platform=instagram"

    updated = accounts.get(db, seeded.id)
    assert updated is not None
    assert updated.username == "renamed.studio"
    assert updated.display_name == "Renamed Studio"
    assert updated.account_type == "CREATOR"


async def test_accounts_edit_rejects_duplicate_handle(
    client: httpx.AsyncClient, db: Database
) -> None:
    """Editing one account to another existing handle → 409 with the matching dialog open."""
    target = accounts.get_by_username(db, "test_artist")
    assert target is not None

    response = await client.post(
        f"/accounts/{target.id}/edit",
        data={
            "username": "test_studio",  # collides with the other seeded IG account
            "display_name": "Test Artist",
            "account_type": "BUSINESS",
        },
    )

    assert response.status_code == 409
    assert "Handle already taken" in response.text
    # The target's edit dialog re-renders open with the failing values.
    expected_dialog_id = f"edit-account-dialog-{target.id}"
    dialog_idx = response.text.find(f'id="{expected_dialog_id}"')
    assert dialog_idx != -1
    assert " open" in response.text[dialog_idx : dialog_idx + 400]


async def test_accounts_edit_missing_id_redirects(client: httpx.AsyncClient) -> None:
    """Editing a missing id 303s to /accounts (idempotent path for stale links)."""
    response = await client.post(
        "/accounts/does-not-exist/edit",
        data={"username": "x", "display_name": "X", "account_type": "BUSINESS"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"


async def test_accounts_delete_removes_row_and_redirects(
    client: httpx.AsyncClient, db: Database
) -> None:
    """POST to ``/accounts/{id}/delete`` removes the row and 303s to ``/accounts``."""
    seeded = accounts.get(db, "178414000000001")
    assert seeded is not None

    response = await client.post(f"/accounts/{seeded.id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"
    assert accounts.get(db, seeded.id) is None


async def test_accounts_delete_unknown_id_no_ops_and_redirects(
    client: httpx.AsyncClient,
) -> None:
    """Deleting an unknown id is a 303 with no DB change — the UI lands on the grid."""
    response = await client.post("/accounts/does-not-exist/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"


async def test_accounts_card_renders_token_days_for_fresh_long_token(
    client: httpx.AsyncClient, db: Database
) -> None:
    """A freshly-issued long token renders an ``Nd`` value with the ``ok`` tone.

    The exact day count is ``60d`` minus a sliver for the time the test took
    to run, so match any positive ``Nd`` ≥ 50 to stay robust under slow CI.
    """
    oauth.issue_token(db, account_id="178414000000001", kind="long")

    response = await client.get("/accounts?platform=instagram")
    assert response.status_code == 200

    studio_block = _card_block(response.text, "@test_studio")
    match = re.search(r'data-token-tone="(\w+)"[^>]*>\s*(\d+)d\b', studio_block)
    assert match is not None, "no token stat rendered in studio card"
    assert match.group(1) == "ok"
    assert int(match.group(2)) >= 50, f"expected ≈60d for fresh long token, got {match.group(2)}d"


async def test_accounts_card_marks_urgent_token(client: httpx.AsyncClient, db: Database) -> None:
    """A long token whose remaining days are ≤ 7 renders the ``urgent`` tone + sr-only hint."""
    long_ago = datetime.now(UTC) - timedelta(days=56)  # 60-day TTL → 4 days remaining
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO oauth_tokens (token, account_id, kind, created_at) VALUES (?, ?, ?, ?)",
            ("mock-long-urgent", "178414000000001", "long", long_ago.isoformat()),
        )

    response = await client.get("/accounts?platform=instagram")
    studio_block = _card_block(response.text, "@test_studio")

    assert 'data-token-tone="urgent"' in studio_block
    # The sr-only marker carries the urgency in text so color isn't load-bearing.
    assert "expires soon" in studio_block


async def test_accounts_card_marks_expired_token(client: httpx.AsyncClient, db: Database) -> None:
    """A long token created long ago renders ``expired`` with the expired tone + sr-only hint."""
    long_ago = datetime.now(UTC) - timedelta(days=120)
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO oauth_tokens (token, account_id, kind, created_at) VALUES (?, ?, ?, ?)",
            ("mock-long-expired", "178414000000001", "long", long_ago.isoformat()),
        )

    response = await client.get("/accounts?platform=instagram")
    studio_block = _card_block(response.text, "@test_studio")

    assert "expired" in studio_block
    assert 'data-token-tone="expired"' in studio_block
    assert "token expired" in studio_block  # sr-only marker


async def test_accounts_view_shows_empty_state_when_all_rows_removed(
    client: httpx.AsyncClient, db: Database
) -> None:
    """With every seed deleted the grid renders the empty-state copy, not stale cards."""
    for acc in accounts.list_all(db):
        accounts.delete(db, acc.id)

    response = await client.get("/accounts")

    assert response.status_code == 200
    assert "No accounts yet" in response.text
