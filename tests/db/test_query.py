"""Tests for :mod:`posthole.db.query` — small SQL-building helpers."""

from __future__ import annotations

import pytest

from posthole.db.query import like_needle


@pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
def test_like_needle_blank_returns_none(raw: str | None) -> None:
    """Blank input short-circuits — caller's ``IS NULL`` guard skips LIKE."""
    assert like_needle(raw) is None


def test_like_needle_wraps_and_lowercases() -> None:
    """Plain input is lower-cased and wrapped in ``%``."""
    assert like_needle("Foo") == "%foo%"


def test_like_needle_strips_whitespace() -> None:
    """Leading/trailing whitespace is stripped before wrapping."""
    assert like_needle("  carousel  ") == "%carousel%"


def test_like_needle_escapes_percent() -> None:
    """``%`` is a SQL LIKE wildcard — escape it so it matches literally."""
    assert like_needle("100%") == r"%100\%%"


def test_like_needle_escapes_underscore() -> None:
    """``_`` is a SQL LIKE wildcard for any single char — escape it."""
    assert like_needle("a_b") == r"%a\_b%"


def test_like_needle_escapes_backslash() -> None:
    """The backslash itself must escape first, before ``%`` and ``_``."""
    assert like_needle(r"C:\Users") == r"%c:\\users%"


def test_like_needle_escapes_all_three_in_one_input() -> None:
    """Inputs containing all three special chars are escaped without collision."""
    assert like_needle(r"a\b%c_d") == r"%a\\b\%c\_d%"
