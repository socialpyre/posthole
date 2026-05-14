"""Reusable tab routing primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TabSpec:
    """Declarative description of a page's tab set.

    ``options`` is an ordered tuple of ``(key, label)`` pairs. The key is
    the URL value (``?<param>=<key>``) and the panel's ``data-panel``
    attribute; the label is the tab button's visible text.

    ``default`` is the option key the URL canonicalizes to — non-default
    keys appear in the URL, the default is stripped so URLs stay clean.
    It must be one of the keys in ``options``.

    ``param`` is the query-string parameter name. Defaults to ``"view"``
    (matches the posts page); other pages can pick ``"tab"``,
    ``"section"``, etc.
    """

    options: tuple[tuple[str, str], ...]
    default: str
    param: str = "view"

    def __post_init__(self) -> None:
        """Validate the spec."""
        if not self.options:
            msg = "TabSpec.options must declare at least one tab"
            raise ValueError(msg)

        non_lower = [k for k, _ in self.options if k != k.lower()]
        if non_lower:
            msg = f"TabSpec option keys must be lowercase; got {non_lower!r}"
            raise ValueError(msg)

        if self.default not in self.keys:
            msg = f"TabSpec default {self.default!r} not in options {self.keys!r}"
            raise ValueError(msg)

    @property
    def keys(self) -> tuple[str, ...]:
        """Tuple of option keys, in declaration order."""
        return tuple(k for k, _ in self.options)

    def normalize(self, raw: str | None) -> str:
        """Coerce a raw query-param value into a valid option key."""
        if raw is None:
            return self.default

        normalized = raw.strip().lower()
        if normalized in self.keys:
            return normalized

        return self.default
