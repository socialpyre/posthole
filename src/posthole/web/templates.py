"""Jinja template loader and environment configuration."""

from pathlib import Path

from fastapi_hotwire import HotwireTemplates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def build_templates() -> HotwireTemplates:
    """Construct the HotwireTemplates instance and register filters and globals."""
    templates = HotwireTemplates(directory=TEMPLATES_DIR)

    # Register custom Jinja filters via templates.env.filters["name"] = fn
    # Register custom globals via templates.env.globals["name"] = value
    return templates  # noqa: RET504  -- comments above mark the extension point
