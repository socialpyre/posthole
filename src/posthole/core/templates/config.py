"""Jinja template loader and environment configuration."""

from pathlib import Path

from fastapi_hotwire import HotwireTemplates

from posthole.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def build_templates() -> HotwireTemplates:
    """Construct the singleton ``HotwireTemplates`` instance."""
    instance = HotwireTemplates(directory=TEMPLATES_DIR)
    _register_globals(instance)
    return instance


def _register_globals(instance: HotwireTemplates) -> None:
    """Register process-static values as Jinja globals.

    Extension point: add new settings-derived statics here. For per-request
    values, use :mod:`posthole.core.templates.middleware` instead.
    """
    settings = get_settings()

    # Jinja's stubs type ``env.globals`` values as a narrow union of its
    # built-in helpers (range, dict, lipsum, …) and reject user-added
    # primitives. The dict accepts any value at runtime.
    instance.env.globals["DEV_RELOAD"] = settings.dev_reload  # ty: ignore[invalid-assignment]


templates = build_templates()
