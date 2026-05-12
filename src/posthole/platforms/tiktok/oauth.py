"""TikTok OAuth route handlers — picker, token exchange, /user/info.

TikTok's OAuth flow is simpler than Meta's:

    GET  /auth/authorize/       → HTML picker
    POST /auth/authorize/       → 302 redirect with ?code=&state=
    POST /oauth/token/          → both grant_type=authorization_code AND
                                  grant_type=refresh_token (returns access+refresh)
    GET  /user/info/            → bearer-authed account info

Tokens use TikTok's real prefixes: ``act.`` for access, ``rft.`` for refresh.

The ``/oauth/token/`` endpoint returns a **flat OAuth2 body** — no
:func:`tiktok_envelope` wrapping. Every other endpoint here uses the
envelope.

Handlers raise platform-specific exceptions from
:mod:`posthole.platforms.tiktok.exceptions`; the central handler converts
them to TikTok dual-envelope JSON.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Header, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from posthole.db import DbDep  # noqa: TC001 — runtime-evaluated by FastAPI Depends
from posthole.platforms.helpers import is_safe_redirect_uri
from posthole.platforms.tiktok.auth import require_bearer
from posthole.platforms.tiktok.exceptions import (
    InvalidGrantError,
    InvalidRedirectUriError,
    UnknownAccountIdError,
    UserNotFoundError,
)
from posthole.platforms.tiktok.responses import (
    TIKTOK_ERROR_RESPONSES,
    tiktok_envelope,
)

if TYPE_CHECKING:
    from fastapi_hotwire import HotwireTemplates


# TikTok's documented token TTLs.
ACCESS_TOKEN_EXPIRES_IN = 86_400  # 24h
REFRESH_TOKEN_EXPIRES_IN = 31_536_000  # 365d


def build_router(templates: HotwireTemplates) -> APIRouter:
    """Return an :class:`APIRouter` with the TikTok OAuth endpoints."""
    router = APIRouter(tags=["tiktok-oauth"], responses=TIKTOK_ERROR_RESPONSES)

    @router.get("/auth/authorize/", response_class=HTMLResponse)
    async def authorize_get(
        request: Request,
        db: DbDep,
        client_key: Annotated[str, Query()] = "",
        redirect_uri: Annotated[str, Query()] = "",
        scope: Annotated[str, Query()] = "",
        state: Annotated[str, Query()] = "",
        response_type: Annotated[str, Query()] = "code",  # noqa: ARG001
    ) -> HTMLResponse:
        """Render the account picker scoped to ``platform="tiktok"``."""
        return templates.TemplateResponse(
            request,
            "tiktok/authorize.html.j2",
            {
                "client_key": client_key,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "accounts": db.accounts.list_all(platform="tiktok"),
            },
        )

    @router.post("/auth/authorize/")
    async def authorize_post(
        db: DbDep,
        account_id: Annotated[str, Form()],
        redirect_uri: Annotated[str, Form()],
        state: Annotated[str, Form()] = "",
    ) -> RedirectResponse:
        """Issue an auth code; 302 redirect back to the client's ``redirect_uri``."""
        if not is_safe_redirect_uri(redirect_uri):
            raise InvalidRedirectUriError
        account = db.accounts.get(account_id)
        if account is None or account.platform != "tiktok":
            raise UnknownAccountIdError
        code_ctx = db.oauth.issue_code(
            account_id=account_id,
            redirect_uri=redirect_uri,
            state=state,
        )
        sep = "&" if "?" in redirect_uri else "?"
        target = f"{redirect_uri}{sep}{urlencode({'code': code_ctx.code, 'state': state})}"
        return RedirectResponse(target, status_code=302)

    @router.post("/oauth/token/")
    async def token(
        db: DbDep,
        grant_type: Annotated[str, Form()],
        client_key: Annotated[str, Form()] = "",  # noqa: ARG001
        client_secret: Annotated[str, Form()] = "",  # noqa: ARG001
        code: Annotated[str, Form()] = "",
        redirect_uri: Annotated[str, Form()] = "",  # noqa: ARG001
        refresh_token: Annotated[str, Form()] = "",
    ) -> dict[str, Any]:
        """Exchange code → access+refresh, OR refresh → rotated pair.

        Returns a **flat** OAuth2 response (no ``tiktok_envelope`` wrapping) —
        this is the one TikTok endpoint that doesn't dual-envelope.
        """
        if grant_type == "authorization_code":
            ctx = db.oauth.consume_code(code)
            if ctx is None:
                msg = "Invalid authorization code"
                raise InvalidGrantError(msg)
            account_id = ctx.account_id
        elif grant_type == "refresh_token":
            tok = db.oauth.get_token(refresh_token)
            if tok is None or tok.kind != "refresh":
                msg = "Invalid refresh token"
                raise InvalidGrantError(msg)
            account_id = tok.account_id
        else:
            msg = f"Unsupported grant_type {grant_type!r}"
            raise InvalidGrantError(msg)

        access = db.oauth.issue_token(account_id=account_id, kind="short", prefix="act.")
        refresh = db.oauth.issue_token(account_id=account_id, kind="refresh", prefix="rft.")
        return {
            "access_token": access.token,
            "expires_in": ACCESS_TOKEN_EXPIRES_IN,
            "open_id": account_id,
            "refresh_token": refresh.token,
            "refresh_expires_in": REFRESH_TOKEN_EXPIRES_IN,
            "scope": "user.info.basic,video.publish",
            "token_type": "Bearer",
        }

    @router.get("/user/info/")
    async def user_info(
        db: DbDep,
        authorization: Annotated[str, Header()] = "",
        fields: Annotated[str, Query()] = "",
    ) -> dict[str, Any]:
        """Return account info, scoped by Bearer-token lookup. Honors ``fields=``."""
        tok = require_bearer(db, authorization)
        account = db.accounts.get(tok.account_id)
        if account is None or account.platform != "tiktok":
            raise UserNotFoundError

        full = {
            "open_id": account.id,
            "union_id": account.id,  # mock: same as open_id
            "avatar_url": account.avatar_url or "",
            "display_name": account.display_name,
        }
        requested = (
            {f.strip() for f in fields.split(",") if f.strip()} if fields else set(full.keys())
        )
        user = {k: v for k, v in full.items() if k in requested}
        return tiktok_envelope({"user": user})

    return router
