"""Template-context builder for the inbox shell."""

from posthole.db import Database, accounts, posts
from posthole.db.posts import Post

INBOX_LIST_LIMIT = 50


def inbox_context(
    db: Database,
    *,
    selected: Post | None = None,
    not_found: bool = False,
) -> dict[str, object]:
    """Build the template context for the inbox shell.

    Templates receive ``Post`` dataclasses directly and resolve usernames
    via the ``usernames`` map, so the row partial doesn't trigger a
    per-row account query. ``accounts.list_all`` is one round-trip and
    the table is small (seeded handful); revisit if it grows.
    """
    rows = posts.list_recent(db, limit=INBOX_LIST_LIMIT)
    usernames = {a.id: a.username for a in accounts.list_all(db)}

    return {
        "posts": rows,
        "total": len(rows),
        "selected": selected,
        "usernames": usernames,
        "not_found": not_found,
    }
