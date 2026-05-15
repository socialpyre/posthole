"""Template-context builder + form validation for the accounts view."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal
from zlib import adler32

from posthole.db import accounts, oauth

if TYPE_CHECKING:
    from posthole.db import Database
    from posthole.db.accounts import Account
    from posthole.db.oauth import LongTokenInfo, TokenKind


# Literal so a typo in ``_token_state`` surfaces at type-check time.
TokenTone = Literal["ok", "urgent", "expired", "missing"]

# IG long: 60d. TikTok refresh: 365d. ``short`` is intentionally excluded.
TOKEN_TTL_DAYS: dict[TokenKind, int] = {"long": 60, "refresh": 365}

TOKEN_URGENT_DAYS = 7

# Alphanumeric runs joined by single dots. Rejects leading/trailing/
# consecutive dots so the value can never resolve to ``.`` or ``..``.
HANDLE_RE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*")

PLATFORM_ACCOUNT_TYPES: dict[str, tuple[str, ...]] = {
    "instagram": ("BUSINESS", "CREATOR", "PERSONAL"),
    "tiktok": ("BUSINESS_ACCOUNT", "CREATOR_ACCOUNT", "PERSONAL_ACCOUNT"),
}

PLATFORM_KEYS: frozenset[str] = frozenset(PLATFORM_ACCOUNT_TYPES)

PLATFORMS: tuple[tuple[str, str], ...] = (
    ("instagram", "Instagram"),
    ("tiktok", "TikTok"),
)

LIVE_WINDOW_MIN = 60

USERNAME_MAX_LEN = 30
DISPLAY_NAME_MAX_LEN = 80


@dataclass(slots=True, frozen=True)
class AccountCardData:
    """Everything the card template needs for one account, pre-derived."""

    account: Account
    intercepted_count: int
    last_seen_label: str
    live: bool
    avatar_seed: int
    token_label: str
    token_tone: TokenTone


@dataclass(slots=True)
class AccountFormState:
    """Create-form values + per-field errors echoed back on validation failure."""

    platform: str = "instagram"
    username: str = ""
    display_name: str = ""
    account_type: str = ""
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class EditFormState:
    """Edit-form state bound to one account; platform is row-supplied, not user-supplied."""

    account_id: str
    platform: str
    username: str = ""
    display_name: str = ""
    account_type: str = ""
    errors: dict[str, str] = field(default_factory=dict)


def accounts_context(
    db: Database,
    *,
    platform: str | None = None,
    form: AccountFormState | None = None,
    open_dialog: bool = False,
    edit_form: EditFormState | None = None,
) -> dict[str, object]:
    """Build the template context for the accounts grid."""
    active_platform = normalize_platform(platform)

    all_accounts = accounts.list_all(db)
    counts = accounts.count_by_platform(db)
    stats = accounts.stats_by_account(db)
    tokens = oauth.latest_long_token_by_account(db)
    now = datetime.now(UTC)

    if active_platform is None:
        visible = all_accounts
    else:
        visible = [a for a in all_accounts if a.platform == active_platform]

    cards: list[AccountCardData] = []
    live_count = 0
    for acc in visible:
        s = stats.get(acc.id)
        last_post_at = s.last_post_at if s else None
        is_live = _is_live(last_post_at, now)
        if is_live:
            live_count += 1
        token_label, token_tone = _token_state(tokens.get(acc.id), now)
        cards.append(
            AccountCardData(
                account=acc,
                intercepted_count=s.intercepted_count if s else 0,
                last_seen_label=_last_seen_label(last_post_at, now),
                live=is_live,
                avatar_seed=adler32(acc.id.encode("utf-8")),
                token_label=token_label,
                token_tone=token_tone,
            )
        )

    return {
        "cards": cards,
        "total": len(visible),
        "live_count": live_count,
        "idle_count": len(visible) - live_count,
        "platform": active_platform or "",
        "platforms": PLATFORMS,
        "counts": {
            "all": len(all_accounts),
            **{k: counts.get(k, 0) for k in PLATFORM_KEYS},
        },
        "form": form or AccountFormState(),
        "platform_account_types": PLATFORM_ACCOUNT_TYPES,
        "open_dialog": open_dialog,
        "edit_form": edit_form,
    }


def normalize_platform(raw: str | None) -> str | None:
    """Coerce a raw ``?platform=`` value into a known key or ``None``."""
    if not raw:
        return None
    lowered = raw.strip().lower()
    return lowered if lowered in PLATFORM_KEYS else None


def validate_new_account(
    *,
    platform: str | None,
    username: str | None,
    display_name: str | None,
    account_type: str | None,
) -> AccountFormState:
    """Validate a create submit; return the form (check ``.errors`` for failures)."""
    form = AccountFormState(
        platform=(platform or "").strip().lower(),
        username=_normalize_username(username),
        display_name=(display_name or "").strip(),
        account_type=(account_type or "").strip().upper(),
    )

    if form.platform not in PLATFORM_KEYS:
        form.errors["platform"] = "Pick a supported platform."

    _validate_common(form, valid_types=PLATFORM_ACCOUNT_TYPES.get(form.platform, ()))
    return form


def validate_edit_account(
    *,
    account_id: str,
    platform: str,
    username: str | None,
    display_name: str | None,
    account_type: str | None,
) -> EditFormState:
    """Validate an edit submit; mirrors :func:`validate_new_account` minus platform."""
    form = EditFormState(
        account_id=account_id,
        platform=platform,
        username=_normalize_username(username),
        display_name=(display_name or "").strip(),
        account_type=(account_type or "").strip().upper(),
    )
    _validate_common(form, valid_types=PLATFORM_ACCOUNT_TYPES.get(platform, ()))
    return form


def _normalize_username(raw: str | None) -> str:
    """Strip whitespace and a single leading ``@``."""
    return (raw or "").strip().removeprefix("@")


def _validate_common(
    form: AccountFormState | EditFormState, *, valid_types: tuple[str, ...]
) -> None:
    """Run the shared field checks; mutates ``form.errors`` in place."""
    if not form.username:
        form.errors["username"] = "Handle is required."
    elif len(form.username) > USERNAME_MAX_LEN:
        form.errors["username"] = f"Handle must be ≤ {USERNAME_MAX_LEN} characters."
    elif not HANDLE_RE.fullmatch(form.username):
        form.errors["username"] = "Handle can only contain letters, digits, dot, or underscore."

    if not form.display_name:
        form.errors["display_name"] = "Display name is required."
    elif len(form.display_name) > DISPLAY_NAME_MAX_LEN:
        form.errors["display_name"] = f"Display name must be ≤ {DISPLAY_NAME_MAX_LEN} characters."

    if form.account_type and form.account_type not in valid_types:
        form.errors["account_type"] = "Pick an account type for this platform."
    elif not form.account_type:
        form.errors["account_type"] = "Account type is required."


def _is_live(last_post_at: datetime | None, now: datetime) -> bool:
    """``True`` if the account captured a post within :data:`LIVE_WINDOW_MIN` minutes."""
    if last_post_at is None:
        return False
    return (now - last_post_at).total_seconds() / 60 <= LIVE_WINDOW_MIN


def _token_state(token: LongTokenInfo | None, now: datetime) -> tuple[str, TokenTone]:
    """Return ``(label, tone)`` for the card's token-expiry stat."""
    if token is None:
        return ("—", "missing")
    ttl = TOKEN_TTL_DAYS.get(token.kind)
    if ttl is None:
        return ("—", "missing")
    remaining = timedelta(days=ttl) - (now - token.created_at)
    days = remaining.days
    if days < 0:
        return ("expired", "expired")
    if days <= TOKEN_URGENT_DAYS:
        return (f"{days}d", "urgent")
    return (f"{days}d", "ok")


def _last_seen_label(last_post_at: datetime | None, now: datetime) -> str:
    """Humanize time since last capture (``4m`` / ``2h`` / ``3d``)."""
    if last_post_at is None:
        return "—"
    minutes = max(0, int((now - last_post_at).total_seconds() // 60))
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"
