"""Instagram publishing route handlers — container, status, publish.

IG Graph's publishing flow is two-step:

    POST /{user_id}/media       → creates a "container" with the media URL
    GET  /{container_id}        → poll for FINISHED status (we return immediately)
    POST /{user_id}/media_publish (creation_id=...) → flip to published

Phase 1 supports IMAGE only. VIDEO / REELS / STORIES / CAROUSEL come in a
follow-up alongside the ``post_media`` table.

Note: ``GET /{container_id}`` is a single-segment wildcard at the root, so the
IG router must be registered AFTER the UI router in ``main.py`` — otherwise
``/accounts`` would resolve here as a missing container.

Handlers omit explicit return type annotations — happy paths return a dict
(FastAPI serializes) while error paths return a Meta-shaped JSONResponse.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Form, Query

from posthole.db import DbDep  # noqa: TC001 — runtime-evaluated by FastAPI Depends
from posthole.platforms.instagram.responses import meta_error


def _invalid_access_token() -> object:
    return meta_error(
        status=401,
        message="Invalid OAuth access token",
        error_type="OAuthException",
        code=190,
    )


def build_router() -> APIRouter:
    """Return an :class:`APIRouter` with the Instagram publishing endpoints."""
    router = APIRouter(tags=["instagram-publishing"])

    @router.post("/{user_id}/media")
    async def create_container(
        user_id: str,
        db: DbDep,
        access_token: Annotated[str, Query()] = "",
        image_url: Annotated[str, Form()] = "",
        caption: Annotated[str, Form()] = "",
        media_type: Annotated[str, Form()] = "IMAGE",
    ):
        """Create a media container — phase 1 supports IMAGE only."""
        if not access_token or db.oauth.get_token(access_token) is None:
            return _invalid_access_token()
        if media_type != "IMAGE":
            return meta_error(
                status=400,
                message=f"Phase 1 only supports media_type=IMAGE (got {media_type!r})",
                code=100,
            )
        if not image_url:
            return meta_error(
                status=400,
                message="image_url is required for IMAGE containers",
                code=100,
                error_subcode=2207001,
            )
        container_id = f"mock-container-{secrets.token_urlsafe(16)}"
        db.posts.create(
            platform="instagram",
            account_id=user_id,
            caption=caption or None,
            external_ref=container_id,
            media_url=image_url,
            media_type="IMAGE",
        )
        return {"id": container_id}

    @router.get("/{container_id}")
    async def container_status(
        container_id: str,
        db: DbDep,
        access_token: Annotated[str, Query()] = "",
    ):
        """Return container status — always ``FINISHED`` in phase 1 (no async sim)."""
        if not access_token or db.oauth.get_token(access_token) is None:
            return _invalid_access_token()
        post = db.posts.get_by_external_ref(container_id)
        if post is None:
            return meta_error(
                status=404,
                message=f"Container {container_id!r} not found",
                code=100,
            )
        return {
            "status_code": "FINISHED",
            "media_type": "IMAGE",
            "media_product_type": "FEED",
        }

    @router.post("/{user_id}/media_publish")
    async def publish(
        user_id: str,  # noqa: ARG001 — IG's URL shape; we publish by container_id
        db: DbDep,
        creation_id: Annotated[str, Form()],
        access_token: Annotated[str, Query()] = "",
    ):
        """Flip a pending container to ``published`` and return its platform-side id."""
        if not access_token or db.oauth.get_token(access_token) is None:
            return _invalid_access_token()
        platform_post_id = f"mock-post-{secrets.token_urlsafe(16)}"
        updated = db.posts.mark_published_by_external_ref(creation_id, platform_post_id)
        if updated is None:
            return meta_error(
                status=404,
                message=f"Container {creation_id!r} not found",
                code=100,
            )
        return {"id": platform_post_id}

    return router
