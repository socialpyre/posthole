"""Tests for the SQLite-backed storage layer."""

from pathlib import Path

import pytest

from posthole.db import Database, accounts, oauth, posts
from posthole.db.migrations import load as load_migrations
from posthole.db.posts import Media


def test_migrations_idempotent_across_reopen(tmp_path: Path) -> None:
    """Opening the same file twice doesn't re-apply any migrations."""
    path = str(tmp_path / "posthole.db")
    first = Database(path)
    with first.cursor() as cur:
        cur.execute("SELECT version FROM schema_version ORDER BY version")
        first_versions = [row[0] for row in cur.fetchall()]
    first.close()

    second = Database(path)
    try:
        with second.cursor() as cur:
            cur.execute("SELECT version FROM schema_version ORDER BY version")
            second_versions = [row[0] for row in cur.fetchall()]
    finally:
        second.close()

    assert first_versions == second_versions
    # Versions should be contiguous starting at 0.
    assert first_versions == list(range(len(first_versions)))


def test_post_round_trip(db: Database) -> None:
    """``create`` returns a Post; ``get`` returns the same fields."""
    created = posts.create(db, platform="instagram", account_id="acc_1", caption="hello")
    fetched = posts.get(db, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.platform == "instagram"
    assert fetched.account_id == "acc_1"
    assert fetched.caption == "hello"
    assert fetched.status == "pending"
    assert fetched.published_at is None
    assert fetched.failure_reason is None


def test_post_mark_published_sets_status_and_timestamp(db: Database) -> None:
    created = posts.create(db, platform="instagram", account_id="acc_1", caption="hi")

    published = posts.mark_published(db, created.id)

    assert published is not None
    assert published.status == "published"
    assert published.published_at is not None


def test_post_mark_failed_records_reason(db: Database) -> None:
    created = posts.create(db, platform="instagram", account_id="acc_1", caption="hi")

    failed = posts.mark_failed(db, created.id, "rate-limited")

    assert failed is not None
    assert failed.status == "failed"
    assert failed.failure_reason == "rate-limited"


def test_post_mark_published_returns_none_when_missing(db: Database) -> None:
    """UPDATE-then-SELECT path returns None when no row matches — non-obvious from the SQL alone."""
    assert posts.mark_published(db, "does-not-exist") is None


def test_post_create_round_trips_optional_fields(db: Database) -> None:
    """``external_ref``, ``media_url``, ``media_type`` survive the round trip."""
    created = posts.create(
        db,
        platform="instagram",
        account_id="acc_1",
        external_ref="mock-container-xyz",
        media_url="https://example.com/img.jpg",
        media_type="IMAGE",
    )

    fetched = posts.get(db, created.id)
    assert fetched is not None
    assert fetched.external_ref == "mock-container-xyz"
    assert fetched.media_url == "https://example.com/img.jpg"
    assert fetched.media_type == "IMAGE"


def test_post_create_with_media_list_round_trips(db: Database) -> None:
    """Carousel posts: ``media=[...]`` survives JSON serialization in media_items."""
    created = posts.create(
        db,
        platform="instagram",
        account_id="acc_1",
        media=[
            Media(ordinal=0, kind="IMAGE", url="https://example.com/1.jpg"),
            Media(ordinal=1, kind="IMAGE", url="https://example.com/2.jpg"),
            Media(ordinal=2, kind="VIDEO", url="https://example.com/3.mp4"),
        ],
    )

    fetched = posts.get(db, created.id)
    assert fetched is not None
    assert len(fetched.media) == 3
    assert [m.ordinal for m in fetched.media] == [0, 1, 2]
    assert [m.kind for m in fetched.media] == ["IMAGE", "IMAGE", "VIDEO"]
    assert fetched.media[2].url == "https://example.com/3.mp4"


def test_post_media_synthesized_from_legacy_columns(db: Database) -> None:
    """A post created with only media_url loads a 1-item ``media`` list."""
    created = posts.create(
        db,
        platform="instagram",
        account_id="acc_1",
        media_url="https://example.com/single.jpg",
        media_type="IMAGE",
    )

    fetched = posts.get(db, created.id)
    assert fetched is not None
    assert fetched.media == [Media(ordinal=0, kind="IMAGE", url="https://example.com/single.jpg")]


def test_post_demo_carousel_seeded_by_migration_0003(db: Database) -> None:
    """Migration 0003 seeds a 3-item carousel for the inbox demo."""
    fetched = posts.get(db, "demo-carousel-0001")

    assert fetched is not None
    assert fetched.platform == "instagram"
    assert len(fetched.media) == 3
    assert [m.url for m in fetched.media] == [
        "https://picsum.photos/seed/posthole-c1/1080/1080",
        "https://picsum.photos/seed/posthole-c2/1080/1080",
        "https://picsum.photos/seed/posthole-c3/1080/1080",
    ]


def test_post_get_by_external_ref(db: Database) -> None:
    """Lookup-by-external-ref is the path both IG and TT publish flows use."""
    created = posts.create(
        db,
        platform="instagram",
        account_id="acc_1",
        external_ref="ref-42",
    )

    fetched = posts.get_by_external_ref(db, "ref-42")
    assert fetched is not None
    assert fetched.id == created.id
    assert posts.get_by_external_ref(db, "ref-nope") is None


def test_post_mark_published_by_external_ref_mints_platform_post_id(db: Database) -> None:
    """The publish flow looks up by external_ref and stamps the final platform_post_id."""
    posts.create(
        db,
        platform="tiktok",
        account_id="acc_1",
        external_ref="v_pub_xyz",
    )

    updated = posts.mark_published_by_external_ref(db, "v_pub_xyz", "1234567890123456789")
    assert updated is not None
    assert updated.status == "published"
    assert updated.platform_post_id == "1234567890123456789"
    assert posts.mark_published_by_external_ref(db, "ref-nope", "x") is None


def test_post_list_recent_orders_newest_first_and_respects_limit(db: Database) -> None:
    """``list_recent`` returns posts ordered by created_at desc, capped at limit."""
    a = posts.create(db, platform="instagram", account_id="acc_1", caption="a")
    b = posts.create(db, platform="instagram", account_id="acc_1", caption="b")
    c = posts.create(db, platform="instagram", account_id="acc_1", caption="c")

    # Filter out the demo carousel seeded by migration 0003 (older
    # created_at than anything we create in-test) so the assertion is
    # robust to seed additions.
    test_ids = {a.id, b.id, c.id}
    all_posts = [p for p in posts.list_recent(db, limit=10) if p.id in test_ids]
    assert [p.id for p in all_posts] == [c.id, b.id, a.id]

    capped = posts.list_recent(db, limit=2)
    assert [p.id for p in capped] == [c.id, b.id]


# ── Accounts ────────────────────────────────────────────────────────────────


def test_accounts_get_returns_seeded_account(db: Database) -> None:
    """Migration 0001 seeds test_studio (id 178414000000001)."""
    a = accounts.get(db, "178414000000001")

    assert a is not None
    assert a.username == "test_studio"
    assert a.platform == "instagram"


def test_accounts_get_returns_none_for_unknown_id(db: Database) -> None:
    """Unknown account id returns None rather than raising."""
    assert accounts.get(db, "does-not-exist") is None


def test_accounts_get_by_username_returns_seeded_account(db: Database) -> None:
    """Lookup-by-username resolves the same account ``get`` returns by id."""
    a = accounts.get_by_username(db, "test_studio")

    assert a is not None
    assert a.id == "178414000000001"


def test_accounts_get_by_username_returns_none_for_unknown(db: Database) -> None:
    """Unknown username returns None — symmetric with ``get`` miss case."""
    assert accounts.get_by_username(db, "does-not-exist") is None


def test_accounts_list_all_returns_both_platforms_by_default(db: Database) -> None:
    """``list_all()`` with no filter returns IG + TT accounts together."""
    rows = accounts.list_all(db)

    platforms = {a.platform for a in rows}
    assert platforms == {"instagram", "tiktok"}


def test_accounts_list_all_filters_by_platform(db: Database) -> None:
    """``platform=`` narrows to one platform's accounts only."""
    ig_only = accounts.list_all(db, platform="instagram")
    assert ig_only
    assert all(a.platform == "instagram" for a in ig_only)

    tt_only = accounts.list_all(db, platform="tiktok")
    assert tt_only
    assert all(a.platform == "tiktok" for a in tt_only)


# ── OAuth ───────────────────────────────────────────────────────────────────


def test_oauth_issue_and_get_token_round_trip(db: Database) -> None:
    """A freshly issued token is retrievable by its opaque value."""
    tok = oauth.issue_token(db, account_id="acc_1", kind="short")

    fetched = oauth.get_token(db, tok.token)
    assert fetched is not None
    assert fetched.account_id == "acc_1"
    assert fetched.kind == "short"


def test_oauth_get_token_returns_none_for_unknown(db: Database) -> None:
    assert oauth.get_token(db, "does-not-exist") is None


def test_oauth_issue_token_honors_explicit_prefix(db: Database) -> None:
    """TikTok needs ``act.`` / ``rft.`` prefixes — explicit prefix overrides the default."""
    tok = oauth.issue_token(db, account_id="acc_1", kind="short", prefix="act.")

    assert tok.token.startswith("act.")


def test_oauth_issue_token_default_prefix_per_kind(db: Database) -> None:
    """Without an explicit prefix, the default is keyed off ``kind``."""
    short = oauth.issue_token(db, account_id="acc_1", kind="short")
    long_ = oauth.issue_token(db, account_id="acc_1", kind="long")
    refresh = oauth.issue_token(db, account_id="acc_1", kind="refresh")

    assert short.token.startswith("mock-short-")
    assert long_.token.startswith("mock-long-")
    assert refresh.token.startswith("mock-refresh-")


def test_oauth_consume_code_is_one_shot(db: Database) -> None:
    """``consume_code`` returns the code on first call, then deletes it.

    This is a real correctness invariant — re-presenting a consumed code
    must NOT yield a token. Tested at the unit level because the HTTP
    OAuth tests can't fully isolate the consume step from the issue step.
    """
    ctx = oauth.issue_code(
        db,
        account_id="acc_1",
        redirect_uri="http://localhost/cb",
        state="s1",
    )

    first = oauth.consume_code(db, ctx.code)
    assert first is not None
    assert first.account_id == "acc_1"

    # Second call: code is gone, even though we present the same value.
    second = oauth.consume_code(db, ctx.code)
    assert second is None


def test_oauth_consume_code_returns_none_for_unknown(db: Database) -> None:
    assert oauth.consume_code(db, "never-issued") is None


def test_oauth_get_code_does_not_consume(db: Database) -> None:
    """``get_code`` is the peek-without-consume read path."""
    ctx = oauth.issue_code(
        db,
        account_id="acc_1",
        redirect_uri="http://localhost/cb",
        state="s1",
    )

    peeked = oauth.get_code(db, ctx.code)
    assert peeked is not None
    assert peeked.account_id == "acc_1"

    # Code is still consumable — peek didn't delete it.
    consumed = oauth.consume_code(db, ctx.code)
    assert consumed is not None


def test_downgrade_guard_refuses_too_new_schema(tmp_path: Path) -> None:
    """If the DB records a version newer than the binary knows, migrate() raises."""
    path = str(tmp_path / "posthole.db")
    first = Database(path)
    # Forge a future version row directly.
    with first.cursor() as cur:
        cur.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (999,),
        )
    first.close()

    with pytest.raises(RuntimeError, match="downgraded"):
        Database(path)


def test_loader_returns_empty_list_for_empty_directory(tmp_path: Path) -> None:
    """No .sql files → empty MIGRATIONS list (degenerate but valid)."""
    assert load_migrations(tmp_path) == []


def test_loader_reads_files_in_version_order(tmp_path: Path) -> None:
    """Files are returned indexed by version, regardless of filesystem order."""
    (tmp_path / "0002_third.sql").write_text("-- third\n")
    (tmp_path / "0000_first.sql").write_text("-- first\n")
    (tmp_path / "0001_second.sql").write_text("-- second\n")

    loaded = load_migrations(tmp_path)

    assert len(loaded) == 3
    assert "first" in loaded[0]
    assert "second" in loaded[1]
    assert "third" in loaded[2]


def test_loader_rejects_non_numeric_prefix(tmp_path: Path) -> None:
    """A file like 'abc_foo.sql' has no version — fail loud at startup."""
    (tmp_path / "abc_foo.sql").write_text("-- nope\n")

    with pytest.raises(RuntimeError, match="numeric prefix"):
        load_migrations(tmp_path)


def test_loader_rejects_version_gap(tmp_path: Path) -> None:
    """0000 + 0002 with no 0001 is invalid — versions must be contiguous."""
    (tmp_path / "0000_first.sql").write_text("-- first\n")
    (tmp_path / "0002_third.sql").write_text("-- third\n")

    with pytest.raises(RuntimeError, match="gap or duplicate"):
        load_migrations(tmp_path)


def test_loader_rejects_duplicate_version(tmp_path: Path) -> None:
    """Two files at the same version number are caught by the contiguity check."""
    (tmp_path / "0000_alpha.sql").write_text("-- a\n")
    (tmp_path / "0000_beta.sql").write_text("-- b\n")

    with pytest.raises(RuntimeError, match="gap or duplicate"):
        load_migrations(tmp_path)
