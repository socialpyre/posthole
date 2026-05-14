"""Template-context builder for the inbox shell."""

from posthole.core.tabs import TabSpec
from posthole.db import Database, accounts, posts
from posthole.db.posts import Post

INBOX_LIST_LIMIT = 50

VIEWS = TabSpec(
    options=(("preview", "Preview"), ("metadata", "Metadata")),
    default="preview",
)


def inbox_context(
    db: Database,
    *,
    selected: Post | None = None,
    not_found: bool = False,
    q: str | None = None,
    view: str | None = None,
) -> dict[str, object]:
    """Build the template context for the inbox shell."""
    rows = posts.list_recent(db, limit=INBOX_LIST_LIMIT)
    usernames = {a.id: a.username for a in accounts.list_all(db)}

    if q and q.strip():
        needle = q.lower().strip()
        rows = [
            p
            for p in rows
            if needle in (p.caption or "").lower()
            or needle in p.account_id.lower()
            or needle in (usernames.get(p.account_id) or "").lower()
        ]

    return {
        "posts": rows,
        "total": len(rows),
        "selected": selected,
        "usernames": usernames,
        "not_found": not_found,
        "q": q or "",
        "view": VIEWS.normalize(view),
        "views_spec": VIEWS,
    }
