"""Tests for the structured-logging pipeline and correlation middleware."""

import uuid

import httpx
import pytest
from asgi_correlation_id import correlation_id
from pydantic import ValidationError

from posthole.core.config import Settings
from posthole.core.logging.processors import (
    add_correlation_id,
    add_service_metadata,
    redact_sensitive,
)
from posthole.core.logging.terminal import console_renderer

# A real, canonical UUID4 (version digit 4, variant digit a) for round-trip
# checks. Hardcoded so tests are deterministic.
VALID_UUID4 = "f47ac10b-58cc-4372-a567-0e02b2c3d479"


async def test_correlation_id_mirrored_when_valid(client: httpx.AsyncClient) -> None:
    """A UUID in ``X-Request-ID`` is preserved on the response."""
    response = await client.get("/", headers={"X-Request-ID": VALID_UUID4})

    assert response.headers["X-Request-ID"] == VALID_UUID4


async def test_invalid_correlation_id_replaced(client: httpx.AsyncClient) -> None:
    """A non-UUID ``X-Request-ID`` is rejected and a fresh UUID4 is minted."""
    response = await client.get("/", headers={"X-Request-ID": "not-a-uuid"})

    rid = response.headers["X-Request-ID"]
    assert rid != "not-a-uuid"
    assert uuid.UUID(rid).version == 4


async def test_response_has_correlation_id_when_header_absent(client: httpx.AsyncClient) -> None:
    """A request without ``X-Request-ID`` still gets one on the response."""
    response = await client.get("/")

    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4


def test_add_correlation_id_attaches_when_bound() -> None:
    token = correlation_id.set("abc-123")
    try:
        out = add_correlation_id(None, "info", {"event": "test"})
    finally:
        correlation_id.reset(token)

    assert out["request_id"] == "abc-123"


def test_add_correlation_id_skips_when_unbound() -> None:
    out = add_correlation_id(None, "info", {"event": "test"})

    assert "request_id" not in out


def test_add_service_metadata_stamps_defaults() -> None:
    out = add_service_metadata(None, "info", {"event": "x"})

    assert out["service"] == "posthole"
    assert out["env"] == "local"


def test_add_service_metadata_respects_caller_override() -> None:
    out = add_service_metadata(None, "info", {"event": "x", "service": "override"})

    assert out["service"] == "override"


def test_redact_masks_known_secret_key() -> None:
    out = redact_sensitive(None, "info", {"event": "x", "authorization": "Bearer abc"})

    assert out["authorization"] == "[redacted]"


def test_redact_drops_headers_collection() -> None:
    out = redact_sensitive(None, "info", {"event": "x", "headers": {"Cookie": "s=1"}})

    assert out["headers"] == "[redacted-collection]"


def test_redact_walks_nested_dicts() -> None:
    out = redact_sensitive(None, "info", {"event": "x", "user": {"profile": {"password": "p"}}})

    assert out["user"]["profile"]["password"] == "[redacted]"  # noqa: S105


def test_redact_leaves_normal_fields_alone() -> None:
    out = redact_sensitive(None, "info", {"event": "x", "path": "/", "status": 200})

    assert out["path"] == "/"
    assert out["status"] == 200


def test_redact_masks_webhook_signature_keys() -> None:
    """Both hyphenated (header) and underscored (kwarg) signature forms match."""
    out = redact_sensitive(
        None,
        "info",
        {
            "event": "x",
            "x-hub-signature-256": "sha256=abc",
            "x_hub_signature_256": "sha256=def",
            "webhook_secret": "shh",
        },
    )

    assert out["x-hub-signature-256"] == "[redacted]"
    assert out["x_hub_signature_256"] == "[redacted]"
    assert out["webhook_secret"] == "[redacted]"  # noqa: S105


def test_redact_drops_body_payload() -> None:
    """Whole request/response bodies are dropped, not walked field-by-field."""
    out = redact_sensitive(
        None, "info", {"event": "x", "body": {"password": "p"}, "payload": [1, 2]}
    )

    assert out["body"] == "[redacted-collection]"
    assert out["payload"] == "[redacted-collection]"


def test_settings_rejects_unknown_log_level() -> None:
    """``POSTHOLE_LOG_LEVEL`` must be one of the standard level names."""
    with pytest.raises(ValidationError):
        Settings.model_validate({"log_level": "banana"})


def test_settings_rejects_unknown_log_format() -> None:
    """``POSTHOLE_LOG_FORMAT`` must be ``console`` or ``json``."""
    with pytest.raises(ValidationError):
        Settings.model_validate({"log_format": "yaml"})


def test_console_renderer_escapes_ansi_in_value() -> None:
    """User-derived values can't inject terminal escape sequences via log kwargs."""
    rendered = console_renderer(
        None,
        "info",
        {"event": "got request", "level": "info", "path": "/posts\x1b[31mFAKE"},
    )

    # The raw ESC byte must not survive into rendered output — repr() escapes it.
    assert "\x1b[31m" not in rendered
    assert "\\x1b[31mFAKE" in rendered


def test_console_renderer_escapes_ctrl_chars_in_event() -> None:
    """Event strings with CR/LF can't forge fake log lines via the console."""
    rendered = console_renderer(
        None,
        "info",
        {"event": "ok\r      INFO   admin logged in", "level": "info"},
    )

    assert "\r" not in rendered
    assert "\\x0d" in rendered
