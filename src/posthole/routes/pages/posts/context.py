"""Template-context builder for the inbox shell."""

from posthole.core.tabs import TabSpec
from posthole.db import Database, accounts, posts
from posthole.db.posts import Post

INBOX_LIST_LIMIT = 50

PLATFORMS: tuple[tuple[str, str], ...] = (
    ("instagram", "Instagram"),
    ("tiktok", "TikTok"),
)
PLATFORM_KEYS: frozenset[str] = frozenset(k for k, _ in PLATFORMS)

STATUS_KEYS: frozenset[str] = frozenset({"published", "pending", "failed"})

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
    platform: str | None = None,
    status: str | None = None,
    view: str | None = None,
) -> dict[str, object]:
    """Build the template context for the inbox shell."""
    all_accounts = accounts.list_all(db)
    usernames = {a.id: a.username for a in all_accounts}
    display_names = {a.id: a.display_name for a in all_accounts}

    active_platform = normalize_platform(platform)
    active_status = normalize_status(status)

    rows = posts.list_recent(
        db,
        limit=INBOX_LIST_LIMIT,
        platform=active_platform,
        q=q,
        # cast: list_recent's status param is the PostStatus literal; we know
        # active_status is one of those keys because normalize_status filters
        # against STATUS_KEYS (which is the literal's value set).
        status=active_status,  # ty: ignore[invalid-argument-type]
    )

    return {
        "posts": rows,
        "total": len(rows),
        "selected": selected,
        "usernames": usernames,
        "display_names": display_names,
        "not_found": not_found,
        "q": q or "",
        "platform": active_platform or "",
        "platforms": PLATFORMS,
        "status": active_status or "",
        "view": VIEWS.normalize(view),
        "views_spec": VIEWS,
    }


def normalize_platform(raw: str | None) -> str | None:
    """Coerce a raw ``?platform=`` value into a known key or ``None``."""
    if not raw:
        return None
    lowered = raw.strip().lower()
    return lowered if lowered in PLATFORM_KEYS else None


def normalize_status(raw: str | None) -> str | None:
    """Coerce a raw ``?status=`` value into a known key or ``None``."""
    if not raw:
        return None
    lowered = raw.strip().lower()
    return lowered if lowered in STATUS_KEYS else None
