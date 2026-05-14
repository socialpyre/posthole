"""Tests for the reusable :class:`TabSpec`."""

import pytest

from posthole.core.tabs import TabSpec


def test_normalize_returns_default_for_none() -> None:
    """``?view=`` absent → default."""
    spec = TabSpec(options=(("a", "A"), ("b", "B")), default="a")

    assert spec.normalize(None) == "a"


def test_normalize_returns_default_for_unknown() -> None:
    """``?view=garbage`` → default (don't 4xx; this is view UI)."""
    spec = TabSpec(options=(("a", "A"), ("b", "B")), default="a")

    assert spec.normalize("garbage") == "a"


def test_normalize_lowercases() -> None:
    """``?VIEW=B`` → ``"b"`` so hand-typed URLs work."""
    spec = TabSpec(options=(("a", "A"), ("b", "B")), default="a")

    assert spec.normalize("B") == "b"


def test_normalize_returns_known_key() -> None:
    """Valid keys pass through unchanged."""
    spec = TabSpec(options=(("a", "A"), ("b", "B")), default="a")

    assert spec.normalize("b") == "b"


def test_keys_preserves_declaration_order() -> None:
    """``keys`` is a tuple ordered by ``options`` order, not alphabetical."""
    spec = TabSpec(options=(("c", "C"), ("a", "A"), ("b", "B")), default="a")

    assert spec.keys == ("c", "a", "b")


def test_default_not_in_options_raises() -> None:
    """A misconfigured spec is a programming bug — fail at construction."""
    with pytest.raises(ValueError, match="not in options"):
        TabSpec(options=(("a", "A"),), default="b")


def test_empty_options_raises() -> None:
    """A spec with zero tabs is nonsense; reject at construction."""
    with pytest.raises(ValueError, match="at least one tab"):
        TabSpec(options=(), default="")


def test_non_lowercase_keys_raise() -> None:
    """Keys must be lowercase since ``normalize`` lowercases the input.

    Catches an asymmetry where a spec with ``"Preview"`` keys would
    never match ``normalize("preview")``.
    """
    with pytest.raises(ValueError, match="must be lowercase"):
        TabSpec(options=(("Preview", "Preview"),), default="Preview")


def test_normalize_strips_whitespace() -> None:
    """Hand-edited URLs with stray spaces still resolve."""
    spec = TabSpec(options=(("a", "A"), ("b", "B")), default="a")

    assert spec.normalize("  b  ") == "b"


def test_custom_param_name() -> None:
    """``param`` lets pages pick ``?tab=`` etc."""
    spec = TabSpec(options=(("a", "A"),), default="a", param="tab")

    assert spec.param == "tab"
