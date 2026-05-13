"""Tests for the SQLite-backed storage layer."""

from pathlib import Path

import pytest

from posthole.db import Database, posts
from posthole.db.migrations import load as load_migrations


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
