"""Structlog processors used in the posthole logging pipeline.

All processors are pure functions of ``(logger, method_name, event_dict)``
returning a (possibly mutated) ``event_dict``.
"""

from __future__ import annotations

from typing import Any

from asgi_correlation_id import correlation_id

APP_REDACT_KEYS = frozenset(
    {
        # Tokens
        "access_token",
        "bearer_token",
        "id_token",
        "refresh_token",
        # OAuth flow secrets (scoped names; bare "state" matches innocent fields)
        "code_verifier",
        "csrf_token",
        "oauth_state",
        # Webhook signing
        "webhook_secret",
        "webhook_signature",
        # Passwords / passphrases
        "passphrase",
        "password",
        "passwd",
        "pwd",
        # Generic provider secrets
        "api_key",
        "client_secret",
        "private_key",
        "secret",
        "session_secret",
        "token",
        "token_encryption_key",
    }
)

HEADER_REDACT_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "proxy_authorization",
        "x-api-key",
        "x_api_key",
        "x-auth-token",
        "x_auth_token",
        "x-csrf-token",
        "x_csrf_token",
        # Meta-style webhook signing — load-bearing for posthole's mocking domain.
        "x-hub-signature",
        "x_hub_signature",
        "x-hub-signature-256",
        "x_hub_signature_256",
    }
)


REDACT_KEYS: frozenset[str] = APP_REDACT_KEYS | HEADER_REDACT_KEYS

# Whole-subtree drops for keys whose value typically *is* a secret-bearing
# collection — covers the realistic exfil pattern
# ``log.info(headers=dict(request.headers))`` or ``log.info(body=await req.json())``
# where per-key matching can't see what's inside.
DROP_KEYS: frozenset[str] = frozenset(
    {
        "body",
        "cookies",
        "headers",
        "payload",
        "request_body",
        "request_cookies",
        "request_headers",
        "response_body",
        "response_cookies",
        "response_headers",
    }
)

# Mutable module state — set by ``set_metadata`` once at startup, then read by
# ``add_service_metadata`` on every log event. Lowercase (not ALL_CAPS) because
# they're not constants; the names just live at module scope so the processor
# stays a top-level function suitable for structlog's processor chain.
service_name: str = "posthole"
env_name: str = "local"


def add_correlation_id(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Attach the current request's correlation ID as ``request_id``."""
    cid = correlation_id.get()
    if cid and "request_id" not in event_dict:
        event_dict["request_id"] = cid

    return event_dict


def add_service_metadata(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Attach service + env to every log line (caller binds can override)."""
    event_dict.setdefault("service", service_name)
    event_dict.setdefault("env", env_name)

    return event_dict


def redact(value: Any) -> Any:
    """Recursively redact known-sensitive keys inside dicts/lists/tuples."""
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for k, v in value.items():
            kl = str(k).lower()
            if kl in DROP_KEYS:
                out[k] = "[redacted-collection]"
            elif kl in REDACT_KEYS and v not in (None, "", "[redacted]"):
                out[k] = "[redacted]"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        # Always emit a plain tuple; subclassing (e.g. namedtuple) takes
        # positional args, not a generator, and would raise TypeError.
        return tuple(redact(v) for v in value)

    return value


def redact_sensitive(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Mask known sensitive keys before rendering — recursively."""
    return redact(event_dict)


def set_metadata(service: str, env: str) -> None:
    """Install the service + env names stamped onto every log line.

    Called by ``configure_logging`` once at startup; never from request code.
    """
    global service_name, env_name

    service_name = service
    env_name = env
