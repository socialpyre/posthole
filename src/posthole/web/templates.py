"""Jinja template loader and environment configuration.

Templates have access to two flavors of context:

1. **Process-static values** are registered as Jinja globals here
   (``instance.env.globals[...]``) and visible as bare names in every
   template — e.g. ``{% if DEV_RELOAD %}``. Use for values derived from
   settings (cached for the process lifetime).
2. **Per-request values** are stamped onto ``request.state`` by
   :func:`posthole.web.middleware.install_template_context_middleware`
   and read in templates as ``{{ request.state.X }}``. Use for anything
   that varies per request.
"""

from pathlib import Path

from fastapi_hotwire import HotwireTemplates

from posthole.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def build_templates() -> HotwireTemplates:
    """Construct the singleton ``HotwireTemplates`` instance."""
    instance = HotwireTemplates(directory=TEMPLATES_DIR)
    _register_globals(instance)
    return instance


def _register_globals(instance: HotwireTemplates) -> None:
    """Register process-static values as Jinja globals.

    Extension point: add new settings-derived statics here. For per-request
    values, use :mod:`posthole.web.middleware` instead.
    """
    settings = get_settings()
    # Jinja's stubs type ``env.globals`` values as a narrow union of its
    # built-in helpers (range, dict, lipsum, …) and reject user-added
    # primitives. The dict accepts any value at runtime.
    instance.env.globals["DEV_RELOAD"] = settings.dev_reload  # ty: ignore[invalid-assignment]


# Process-singleton — routers import this directly rather than receiving it
# via a factory parameter. The instance is stateless after construction.
templates = build_templates()
