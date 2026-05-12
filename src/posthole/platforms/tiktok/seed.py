"""TikTok seed flow — exercises auth + video init + status fetch in-process.

Uses ``source=PULL_FROM_URL`` to skip the chunked PUT in the seed path —
status_fetch flips the post to published immediately.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.logging import get_logger
from posthole.platforms.helpers import query_param

if TYPE_CHECKING:
    import httpx

logger = get_logger(__name__)

# Account IDs match the rows inserted by migration 0002_multiplatform.sql.
SEED_POSTS: list[tuple[str, str, str]] = [
    (
        "tt-7000000000000000001",
        "https://video.example/clip-1.mp4",
        "first TikTok — golden hour",
    ),
    (
        "tt-7000000000000000002",
        "https://video.example/clip-2.mp4",
        "portrait video from the brand account",
    ),
]


async def seed_flow(client: httpx.AsyncClient) -> int:
    """Publish ``SEED_POSTS`` via the live TikTok routes; return count."""
    for user_id, video_url, caption in SEED_POSTS:
        await _publish_one(client, user_id=user_id, video_url=video_url, caption=caption)
    return len(SEED_POSTS)


async def _publish_one(
    client: httpx.AsyncClient,
    *,
    user_id: str,
    video_url: str,
    caption: str,
) -> None:
    access_token = await _authorize(client, user_id=user_id)

    init = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {"title": caption, "privacy_level": "SELF_ONLY"},
            "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    init.raise_for_status()
    publish_id = init.json()["data"]["publish_id"]

    status = await client.post(
        "/post/publish/status/fetch/",
        json={"publish_id": publish_id},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    status.raise_for_status()
    logger.info("seed published", platform="tiktok", user_id=user_id, caption=caption[:40])


async def _authorize(client: httpx.AsyncClient, *, user_id: str) -> str:
    auth = await client.post(
        "/auth/authorize/",
        data={
            "account_id": user_id,
            "redirect_uri": "http://localhost/seed/callback",
            "state": "seed",
        },
        follow_redirects=False,
    )
    if auth.status_code != 302:
        msg = f"tiktok seed: /auth/authorize/ returned {auth.status_code}: {auth.text[:200]}"
        raise RuntimeError(msg)
    code = query_param(auth.headers["location"], "code")

    token_resp = await client.post(
        "/oauth/token/",
        data={
            "client_key": "seed-client",
            "client_secret": "seed-secret",
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost/seed/callback",
        },
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]
