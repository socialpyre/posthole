"""TikTok publishing route handlers — video init, chunked upload, status fetch.

The IG-equivalent "container → publish" two-step is the TikTok "init → PUT
chunks → status_fetch" three-step. We mock the bytes flow: the PUT handler
accepts chunks, validates ``Content-Range`` is present, and discards.

    POST /post/publish/video/init/  → mint publish_id; return upload_url for FILE_UPLOAD
    PUT  /upload/{publish_id}       → accept chunk bytes; 200 with empty body
    POST /post/publish/status/fetch/ → flip post to published; return PUBLISH_COMPLETE

All paths shown post-strip (real clients send ``/v2/post/...``).
"""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Body, Header, Request

from posthole.db import DbDep  # noqa: TC001 — runtime-evaluated by FastAPI Depends
from posthole.platforms.tiktok._bearer import strip_bearer
from posthole.platforms.tiktok.responses import tiktok_envelope, tiktok_error


def build_router() -> APIRouter:
    """Return an :class:`APIRouter` with the TikTok publishing endpoints."""
    router = APIRouter(tags=["tiktok-publishing"])

    @router.post("/post/publish/video/init/")
    async def init_video(
        request: Request,
        db: DbDep,
        body: Annotated[dict[str, Any], Body()],
        authorization: Annotated[str, Header()] = "",
    ):
        """Create a publish container; return ``publish_id`` + (for FILE_UPLOAD) ``upload_url``."""
        bearer = strip_bearer(authorization)
        tok = db.oauth.get_token(bearer) if bearer else None
        if tok is None:
            return tiktok_error(
                http_status=401, code="access_token_invalid", message="Invalid access token"
            )

        post_info = body.get("post_info", {}) or {}
        source_info = body.get("source_info", {}) or {}
        source = source_info.get("source")
        if source not in ("FILE_UPLOAD", "PULL_FROM_URL"):
            return tiktok_error(
                http_status=400,
                code="invalid_param",
                message=f"source_info.source must be FILE_UPLOAD or PULL_FROM_URL (got {source!r})",
            )

        publish_id = f"v_pub_{secrets.token_urlsafe(20)}"
        media_url = source_info.get("video_url") if source == "PULL_FROM_URL" else "uploading"
        caption = post_info.get("title") or post_info.get("caption") or None

        db.posts.create(
            platform="tiktok",
            account_id=tok.account_id,
            caption=caption,
            external_ref=publish_id,
            media_url=media_url,
            media_type="VIDEO",
        )

        data: dict[str, Any] = {"publish_id": publish_id}
        if source == "FILE_UPLOAD":
            # Mock upload URL pointing back at our own PUT handler. Real
            # TikTok hands out a CDN URL; the shape on the wire is the same.
            base = str(request.base_url).rstrip("/")
            data["upload_url"] = f"{base}/upload/{publish_id}"
        return tiktok_envelope(data)

    @router.put("/upload/{publish_id}")
    async def upload_chunk(
        publish_id: str,
        request: Request,
        db: DbDep,
        content_range: Annotated[str, Header()] = "",
    ):
        """Accept chunk bytes, validate Content-Range header is present, discard body."""
        if not content_range:
            return tiktok_error(
                http_status=400,
                code="invalid_param",
                message="Content-Range header is required for chunked upload",
            )
        post = db.posts.get_by_external_ref(publish_id)
        if post is None or post.platform != "tiktok":
            return tiktok_error(
                http_status=404, code="invalid_param", message=f"Unknown publish_id {publish_id!r}"
            )
        # Drain the body without buffering — we don't store it. Iterate the
        # chunks so very large uploads don't pin memory.
        async for _ in request.stream():
            pass
        return tiktok_envelope({})

    @router.post("/post/publish/status/fetch/")
    async def status_fetch(
        db: DbDep,
        body: Annotated[dict[str, Any], Body()],
        authorization: Annotated[str, Header()] = "",
    ):
        """Look up the publish, flip to published, return PUBLISH_COMPLETE state."""
        bearer = strip_bearer(authorization)
        if not bearer or db.oauth.get_token(bearer) is None:
            return tiktok_error(
                http_status=401, code="access_token_invalid", message="Invalid access token"
            )
        publish_id = body.get("publish_id", "")
        if not publish_id:
            return tiktok_error(
                http_status=400, code="invalid_param", message="publish_id is required"
            )
        post = db.posts.get_by_external_ref(publish_id)
        if post is None or post.platform != "tiktok":
            return tiktok_error(
                http_status=404, code="invalid_param", message=f"Unknown publish_id {publish_id!r}"
            )

        # Mint a TikTok-shaped post id (numeric-ish) and flip to published if not already.
        if post.status != "published":
            platform_post_id = "".join(secrets.choice("0123456789") for _ in range(19))
            updated = db.posts.mark_published_by_external_ref(publish_id, platform_post_id)
            if updated is not None:
                post = updated

        return tiktok_envelope(
            {
                "status": "PUBLISH_COMPLETE",
                # Mirroring TikTok's actual schema typo: "publicaly" not "publicly".
                "publicaly_available_post_id": [post.platform_post_id]
                if post.platform_post_id
                else [],
                "uploaded_bytes": 0,
                "fail_reason": "",
            }
        )

    return router
