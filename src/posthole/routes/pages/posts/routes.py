"""Inbox/Post routes to render the split-pane shell."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from posthole.core.templates import templates
from posthole.db import DbDep, posts
from posthole.routes.pages.posts.context import inbox_context
from posthole.routes.pages.posts.exceptions import PostNotFoundError

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def inbox_view() -> RedirectResponse:
    """Render the inbox view at ``/``."""
    return RedirectResponse("/posts")


@router.get("/posts", response_class=HTMLResponse)
async def posts_view(
    request: Request,
    db: DbDep,
    q: str | None = None,
    view: str | None = None,
) -> HTMLResponse:
    """Render the inbox at ``/posts``; ``?q=`` filters, ``?view=`` selects the tab."""
    return templates.TemplateResponse(
        request,
        "pages/posts/index.html.j2",
        inbox_context(db, q=q, view=view),
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail_view(
    post_id: str,
    request: Request,
    db: DbDep,
    q: str | None = None,
    view: str | None = None,
) -> HTMLResponse:
    """Render a single post; ``?q=`` keeps the list filtered, ``?view=`` selects the tab."""
    selected = posts.get(db, post_id)

    if selected is None:
        raise PostNotFoundError(post_id)

    return templates.TemplateResponse(
        request,
        "pages/posts/index.html.j2",
        inbox_context(db, selected=selected, q=q, view=view),
    )
