"""Jinja template loader and environment configuration."""

from pathlib import Path

from fastapi_hotwire import HotwireTemplates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def build_templates() -> HotwireTemplates:
    """Construct the singleton ``HotwireTemplates`` instance."""
    instance = HotwireTemplates(directory=TEMPLATES_DIR)

    # Register custom Jinja filters via instance.env.filters["name"] = fn
    # Register custom globals via instance.env.globals["name"] = value
    return instance  # noqa: RET504  -- comments above mark the extension point


# Process-singleton — routers import this directly rather than receiving it
# via a factory parameter. The instance is stateless after construction.
templates = build_templates()
