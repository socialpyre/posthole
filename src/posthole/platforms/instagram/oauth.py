"""Instagram OAuth route handlers — picker, code issuance, token exchange, /me.

Modeled after the Meta Graph OAuth flow. Real clients follow this sequence:

    GET  /oauth/authorize      → HTML picker
    POST /oauth/authorize      → 303 redirect to redirect_uri with ?code=&state=
    POST /oauth/access_token   → short-lived token + user_id
    GET  /access_token         → long-lived (60-day) token
    GET  /refresh_access_token → rotate the long-lived token
    GET  /me                   → account info

Tokens carry no platform field — the same OAuth state tables could serve any
future platform. The ``mock-short-`` / ``mock-long-`` prefixes are cosmetic.

Handlers omit explicit return type annotations: their happy path returns a
dict (FastAPI serializes it) while error paths return a Meta-shaped
``JSONResponse`` via :func:`meta_error`. A return-type union would obscure
more than it documents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from posthole.db import DbDep  # noqa: TC001 — runtime-evaluated by FastAPI Depends
from posthole.platforms.helpers import is_safe_redirect_uri
from posthole.platforms.instagram.responses import meta_error

if TYPE_CHECKING:
    from fastapi_hotwire import HotwireTemplates


# Meta's default long-lived token TTL: 60 days = 5_184_000 seconds.
LONG_TOKEN_EXPIRES_IN = 5_184_000


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Return an :class:`APIRouter` with the Instagram OAuth endpoints."""
    router = APIRouter(tags=["instagram-oauth"])

    @router.get("/oauth/authorize", response_class=HTMLResponse)
    async def authorize_get(
        request: Request,
        db: DbDep,
        client_id: Annotated[str, Query()] = "",
        redirect_uri: Annotated[str, Query()] = "",
        scope: Annotated[str, Query()] = "",
        state: Annotated[str, Query()] = "",
        response_type: Annotated[str, Query()] = "code",  # noqa: ARG001
    ) -> HTMLResponse:
        """Render the account picker — user POSTs back to issue a code."""
        return templates.TemplateResponse(
            request,
            "instagram/authorize.html.j2",
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "accounts": db.accounts.list_all(platform="instagram"),
            },
        )

    @router.post("/oauth/authorize")
    async def authorize_post(
        db: DbDep,
        account_id: Annotated[str, Form()],
        redirect_uri: Annotated[str, Form()],
        state: Annotated[str, Form()] = "",
    ):
        """Issue an auth code, redirect back to the client's ``redirect_uri``."""
        if not is_safe_redirect_uri(redirect_uri):
            return meta_error(
                status=400,
                message="redirect_uri must be a loopback http(s) URL",
                error_type="OAuthException",
                code=100,
            )
        if db.accounts.get(account_id) is None:
            return meta_error(
                status=400,
                message=f"Unknown account_id {account_id!r}",
                code=100,
            )
        code_ctx = db.oauth.issue_code(
            account_id=account_id,
            redirect_uri=redirect_uri,
            state=state,
        )
        sep = "&" if "?" in redirect_uri else "?"
        target = f"{redirect_uri}{sep}{urlencode({'code': code_ctx.code, 'state': state})}"
        return RedirectResponse(target, status_code=303)

    @router.post("/oauth/access_token")
    async def access_token_post(
        db: DbDep,
        code: Annotated[str, Form()],
        grant_type: Annotated[str, Form()] = "authorization_code",  # noqa: ARG001
        client_id: Annotated[str, Form()] = "",  # noqa: ARG001
        client_secret: Annotated[str, Form()] = "",  # noqa: ARG001
        redirect_uri: Annotated[str, Form()] = "",  # noqa: ARG001
    ):
        """Exchange a one-shot code for a short-lived access token."""
        ctx = db.oauth.consume_code(code)
        if ctx is None:
            return meta_error(
                status=400,
                message="Invalid authorization code",
                error_type="OAuthException",
                code=100,
                error_subcode=2207001,
            )
        token = db.oauth.issue_token(account_id=ctx.account_id, kind="short")
        return {
            "access_token": token.token,
            "user_id": ctx.account_id,
            "permissions": "",
        }

    @router.get("/access_token")
    async def access_token_exchange(
        db: DbDep,
        access_token: Annotated[str, Query()],
        grant_type: Annotated[str, Query()] = "ig_exchange_token",  # noqa: ARG001
        client_secret: Annotated[str, Query()] = "",  # noqa: ARG001
    ):
        """Exchange a short-lived token for a long-lived (60-day) token."""
        tok = db.oauth.get_token(access_token)
        if tok is None:
            return meta_error(
                status=400,
                message="Invalid access token",
                error_type="OAuthException",
                code=190,
            )
        new_tok = db.oauth.issue_token(account_id=tok.account_id, kind="long")
        return {
            "access_token": new_tok.token,
            "token_type": "bearer",
            "expires_in": LONG_TOKEN_EXPIRES_IN,
        }

    @router.get("/refresh_access_token")
    async def refresh_access_token(
        db: DbDep,
        access_token: Annotated[str, Query()],
        grant_type: Annotated[str, Query()] = "ig_refresh_token",  # noqa: ARG001
    ):
        """Rotate a long-lived token. Refuses short-lived tokens."""
        tok = db.oauth.get_token(access_token)
        if tok is None or tok.kind != "long":
            return meta_error(
                status=400,
                message="Invalid long-lived access token",
                error_type="OAuthException",
                code=190,
            )
        new_tok = db.oauth.issue_token(account_id=tok.account_id, kind="long")
        return {
            "access_token": new_tok.token,
            "token_type": "bearer",
            "expires_in": LONG_TOKEN_EXPIRES_IN,
        }

    @router.get("/me")
    async def me(
        db: DbDep,
        access_token: Annotated[str, Query()],
        fields: Annotated[str, Query()] = "",  # noqa: ARG001
    ):
        """Return the authenticated account's IG-shaped profile."""
        tok = db.oauth.get_token(access_token)
        if tok is None:
            return meta_error(
                status=400,
                message="Invalid access token",
                error_type="OAuthException",
                code=190,
            )
        account = db.accounts.get(tok.account_id)
        if account is None:
            return meta_error(
                status=404,
                message="Account not found",
                code=803,
            )
        return {
            "user_id": account.id,
            "username": account.username,
            "name": account.display_name,
            "profile_picture_url": account.avatar_url,
            "account_type": account.account_type,
        }

    return router
