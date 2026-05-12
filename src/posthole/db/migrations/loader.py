"""Loader for the on-disk ``.sql`` migration files."""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).parent


def load(directory: Path | None = None) -> list[str]:
    """Load ``.sql`` files in ``directory`` (defaults to this package), sorted by version.

    Validates that the version numbers are contiguous (0, 1, 2, ...) and
    returns a list where index ``i`` is the SQL for migration ``i``. The
    ``directory`` parameter exists for testability; production callers should
    accept the default.
    """
    root = directory if directory is not None else _HERE
    entries: list[tuple[int, str]] = []
    for path in sorted(root.glob("*.sql")):
        prefix = path.stem.split("_", 1)[0]
        try:
            version = int(prefix)
        except ValueError as e:
            msg = f"Migration file {path.name!r} must start with a numeric prefix"
            raise RuntimeError(msg) from e
        entries.append((version, path.read_text(encoding="utf-8")))

    for expected, (actual, _) in enumerate(entries):
        if expected != actual:
            msg = (
                f"Migration version gap or duplicate: expected {expected}, "
                f"found {actual}. Files must be numbered contiguously from 0."
            )
            raise RuntimeError(msg)

    return [sql for _, sql in entries]


MIGRATIONS: list[str] = load()
