"""Accounts routes: ``/accounts`` grid + create/edit/delete handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from posthole.core.templates import templates
from posthole.db import DbDep, DuplicateUsernameError, accounts
from posthole.routes.pages.accounts.context import (
    AccountFormState,
    EditFormState,
    accounts_context,
    validate_edit_account,
    validate_new_account,
)

if TYPE_CHECKING:
    from posthole.db.database import Database


router = APIRouter()


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_view(
    request: Request,
    db: DbDep,
    platform: str | None = None,
) -> HTMLResponse:
    """Render the accounts grid; ``?platform=`` scopes the visible cards."""
    return templates.TemplateResponse(
        request,
        "pages/accounts/index.html.j2",
        accounts_context(db, platform=platform),
    )


@router.post("/accounts/new", response_class=HTMLResponse, response_model=None)
async def accounts_create(
    request: Request,
    db: DbDep,
    platform: str = Form(default=""),
    username: str = Form(default=""),
    display_name: str = Form(default=""),
    account_type: str = Form(default=""),
) -> HTMLResponse | RedirectResponse:
    """Create a new mock account; 303 to the platform-filtered grid on success."""
    form = validate_new_account(
        platform=platform,
        username=username,
        display_name=display_name,
        account_type=account_type,
    )
    if form.errors:
        return _render_create_form(request, db, form, status_code=400)

    try:
        accounts.create(
            db,
            platform=form.platform,
            username=form.username,
            display_name=form.display_name,
            account_type=form.account_type,
        )
    except DuplicateUsernameError:
        form.errors["username"] = "Handle already taken on this platform."
        return _render_create_form(request, db, form, status_code=409)
    return RedirectResponse(url=f"/accounts?platform={form.platform}", status_code=303)


@router.post("/accounts/{account_id}/edit", response_class=HTMLResponse, response_model=None)
async def accounts_edit(
    account_id: str,
    request: Request,
    db: DbDep,
    username: str = Form(default=""),
    display_name: str = Form(default=""),
    account_type: str = Form(default=""),
) -> HTMLResponse | RedirectResponse:
    """Update an account's mutable fields. Platform is immutable; missing row → /accounts."""
    current = accounts.get(db, account_id)
    if current is None:
        return RedirectResponse(url="/accounts", status_code=303)

    form = validate_edit_account(
        account_id=account_id,
        platform=current.platform,
        username=username,
        display_name=display_name,
        account_type=account_type,
    )
    if form.errors:
        return _render_edit_form(request, db, form, status_code=400)

    try:
        updated = accounts.update(
            db,
            account_id,
            username=form.username,
            display_name=form.display_name,
            account_type=form.account_type,
        )
    except DuplicateUsernameError:
        form.errors["username"] = "Handle already taken on this platform."
        return _render_edit_form(request, db, form, status_code=409)
    if updated is None:
        # Row was deleted between get and update — don't fake a successful save.
        return RedirectResponse(url="/accounts", status_code=303)
    return RedirectResponse(url=f"/accounts?platform={current.platform}", status_code=303)


@router.post("/accounts/{account_id}/delete", response_class=RedirectResponse)
async def accounts_delete(account_id: str, db: DbDep) -> RedirectResponse:
    """Delete an account row (missing ids no-op)."""
    accounts.delete(db, account_id)
    return RedirectResponse(url="/accounts", status_code=303)


def _render_create_form(
    request: Request, db: Database, form: AccountFormState, *, status_code: int
) -> HTMLResponse:
    """Re-render the grid with the create dialog open + failing values."""
    return templates.TemplateResponse(
        request,
        "pages/accounts/index.html.j2",
        accounts_context(
            db,
            platform=request.query_params.get("platform"),
            form=form,
            open_dialog=True,
        ),
        status_code=status_code,
    )


def _render_edit_form(
    request: Request, db: Database, form: EditFormState, *, status_code: int
) -> HTMLResponse:
    """Re-render the grid with the matching card's edit dialog open + failing values."""
    return templates.TemplateResponse(
        request,
        "pages/accounts/index.html.j2",
        accounts_context(db, platform=request.query_params.get("platform"), edit_form=form),
        status_code=status_code,
    )
