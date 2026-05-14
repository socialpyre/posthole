"""Jinja template loader and environment configuration."""

from pathlib import Path

from fastapi_hotwire import HotwireTemplates

from posthole.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def build_templates() -> HotwireTemplates:
    """Construct the singleton ``HotwireTemplates`` instance."""
    instance = HotwireTemplates(directory=TEMPLATES_DIR)

    _register_globals(instance)
    _register_tests(instance)

    return instance


def _register_globals(instance: HotwireTemplates) -> None:
    """Register process-static values as Jinja globals."""
    settings = get_settings()

    # Jinja's stubs type ``env.globals`` values as a narrow union of its
    # built-in helpers (range, dict, lipsum, …) and reject user-added
    # primitives. The dict accepts any value at runtime.
    instance.env.globals["DEV_RELOAD"] = settings.dev_reload  # ty: ignore[invalid-assignment]


def _register_tests(instance: HotwireTemplates) -> None:
    """Register Jinja tests shared across templates."""
    # Jinja's stubs type ``env.tests`` values as a narrow union of its
    # built-in test signatures and reject our two-arg form. The dict
    # accepts any callable at runtime.
    instance.env.tests["current_for"] = _current_for  # ty: ignore[invalid-assignment]


def _current_for(request_path: str, link_path: str) -> bool:
    """Hierarchical route match for nav-link ``aria-current``."""
    return request_path == link_path or request_path.startswith(link_path + "/")


templates = build_templates()
