"""Reusable query primitives — small helpers for safe SQL construction."""

from __future__ import annotations


def like_needle(raw: str | None) -> str | None:
    """Normalize a user search string into a SQL LIKE pattern, or ``None`` if blank.

    Returns the wrapped ``%needle%`` form with ``%``, ``_``, and ``\\``
    backslash-escaped so a user searching ``"50%"`` doesn't accidentally
    match everything. Callers MUST pair this with ``ESCAPE '\\'`` in
    their SQL — without it, the escapes are treated as literal characters
    and the LIKE clause silently misbehaves.

    Blank or whitespace-only input returns ``None`` so the caller's
    ``:like_q IS NULL OR ...`` guard short-circuits the LIKE branch
    entirely; this keeps "no search" as cheap as it was before search
    existed.

    Lower-cases the needle because SQLite's default LIKE is ASCII
    case-insensitive on the right side but byte-exact on the left —
    matching the platform/content scope here (ASCII English) without
    pulling in ``LOWER(...)`` or ``COLLATE NOCASE`` SQL wrapping.
    """
    if not raw:
        return None
    needle = raw.strip().lower()
    if not needle:
        return None
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
