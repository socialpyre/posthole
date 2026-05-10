"""Smoke tests for template path resolution."""

from posthole.web.templates import build_templates


def test_app_layout_resolves() -> None:
    """The root layout template loads via the configured loader."""
    templates = build_templates()
    assert templates.get_template("layouts/app.html.j2")


def test_inbox_index_resolves() -> None:
    """The inbox page template loads at its expected path."""
    templates = build_templates()
    assert templates.get_template("pages/inbox/index.html.j2")
