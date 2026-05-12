"""Cross-platform helpers used by per-platform code.

Imported by ``platforms/<name>/seed.py`` modules. Lives at the
``platforms`` package root (not under any one platform) because the helpers
are shared across all of them.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

# Loopback hosts allowed as OAuth redirect targets. Real Meta/TikTok require
# pre-registered redirect URIs; the mock isn't a registration server, so we
# clamp to loopback to keep the "developer machine" assumption honest.
_ALLOWED_REDIRECT_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def query_param(url: str, key: str) -> str:
    """Return the first value for ``key`` in ``url``'s query string.

    Raises :class:`RuntimeError` with a clear message if the key is missing —
    seed flows surface this as "the OAuth redirect didn't contain what we
    expected" without crashing into a less informative ``KeyError``.
    """
    values = parse_qs(urlparse(url).query).get(key, [])
    if not values:
        msg = f"redirect URL missing ?{key}= in {url!r}"
        raise RuntimeError(msg)
    return values[0]


def is_safe_redirect_uri(uri: str) -> bool:
    """Return whether ``uri`` is a loopback HTTP(S) URL safe to redirect to.

    Refuses non-http(s) schemes (rejects ``javascript:`` payloads) and any
    host other than ``localhost`` / ``127.0.0.1`` / ``::1``. ``urlparse`` is
    careful to strip ``userinfo@`` from ``.hostname``, so ``http://localhost@
    evil.example`` is rejected on the host check.
    """
    try:
        parts = urlparse(uri)
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"}:
        return False
    return parts.hostname in _ALLOWED_REDIRECT_HOSTS
