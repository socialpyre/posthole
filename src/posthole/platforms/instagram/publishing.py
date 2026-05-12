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

Handlers raise platform-specific exceptions from
:mod:`posthole.platforms.instagram.exceptions`; the central handler
converts them to Meta-shaped JSON envelopes.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Form, Query

from posthole.db import DbDep  # noqa: TC001 — runtime-evaluated by FastAPI Depends
from posthole.platforms.instagram.auth import require_access_token
from posthole.platforms.instagram.exceptions import (
    ContainerNotFoundError,
    MissingImageUrlError,
    UnsupportedMediaTypeError,
)
from posthole.platforms.instagram.responses import META_ERROR_RESPONSES


def build_router() -> APIRouter:
    """Return an :class:`APIRouter` with the Instagram publishing endpoints."""
    router = APIRouter(tags=["instagram-publishing"], responses=META_ERROR_RESPONSES)

    @router.post("/{user_id}/media")
    async def create_container(
        user_id: str,
        db: DbDep,
        access_token: Annotated[str, Query()] = "",
        image_url: Annotated[str, Form()] = "",
        caption: Annotated[str, Form()] = "",
        media_type: Annotated[str, Form()] = "IMAGE",
    ) -> dict[str, str]:
        """Create a media container — phase 1 supports IMAGE only."""
        require_access_token(db, access_token)
        if media_type != "IMAGE":
            msg = f"Phase 1 only supports media_type=IMAGE (got {media_type!r})"
            raise UnsupportedMediaTypeError(msg)
        if not image_url:
            raise MissingImageUrlError
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
    ) -> dict[str, str]:
        """Return container status — always ``FINISHED`` in phase 1 (no async sim)."""
        require_access_token(db, access_token)
        post = db.posts.get_by_external_ref(container_id)
        if post is None:
            msg = f"Container {container_id!r} not found"
            raise ContainerNotFoundError(msg)
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
    ) -> dict[str, str]:
        """Flip a pending container to ``published`` and return its platform-side id."""
        require_access_token(db, access_token)
        platform_post_id = f"mock-post-{secrets.token_urlsafe(16)}"
        updated = db.posts.mark_published_by_external_ref(creation_id, platform_post_id)
        if updated is None:
            msg = f"Container {creation_id!r} not found"
            raise ContainerNotFoundError(msg)
        return {"id": platform_post_id}

    return router
