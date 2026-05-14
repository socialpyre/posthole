"""Jinja template subsystem: loader, Jinja globals, per-request state middleware."""

from posthole.core.templates.config import TEMPLATES_DIR, build_templates, templates
from posthole.core.templates.middleware import TemplateContextMiddleware

__all__ = [
    "TEMPLATES_DIR",
    "TemplateContextMiddleware",
    "build_templates",
    "templates",
]
