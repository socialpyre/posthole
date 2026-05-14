"""Instagram seed flow — exercises the IG OAuth + publish endpoints in-process."""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.core.logging import get_logger
from posthole.routes.platforms.helpers import query_param

if TYPE_CHECKING:
    import httpx

logger = get_logger(__name__)

# Account IDs match the rows inserted by migration 0001_instagram.sql.
SEED_POSTS: list[tuple[str, str, str]] = [
    (
        "178414000000001",
        "https://picsum.photos/seed/posthole-1/1080/1080",
        "first published post — golden hour",
    ),
    (
        "178414000000001",
        "https://picsum.photos/seed/posthole-2/1080/1080",
        "second post with #hashtags and a https://example.com link",
    ),
    (
        "178414000000002",
        "https://picsum.photos/seed/posthole-3/1080/1350",
        "portrait 4:5 from the other account",
    ),
]


async def seed_flow(client: httpx.AsyncClient) -> int:
    """Publish ``SEED_POSTS`` via the live IG routes; return count."""
    for user_id, image_url, caption in SEED_POSTS:
        await _publish_one(client, user_id=user_id, image_url=image_url, caption=caption)
    return len(SEED_POSTS)


async def _publish_one(
    client: httpx.AsyncClient,
    *,
    user_id: str,
    image_url: str,
    caption: str,
) -> None:
    access_token = await _authorize(client, user_id=user_id)

    container = await client.post(
        f"/{user_id}/media",
        data={"image_url": image_url, "caption": caption},
        params={"access_token": access_token},
    )
    container.raise_for_status()
    container_id = container.json()["id"]

    publish = await client.post(
        f"/{user_id}/media_publish",
        data={"creation_id": container_id},
        params={"access_token": access_token},
    )
    publish.raise_for_status()
    logger.info("seed published", platform="instagram", user_id=user_id, caption=caption[:40])


async def _authorize(client: httpx.AsyncClient, *, user_id: str) -> str:
    auth = await client.post(
        "/oauth/authorize",
        data={
            "account_id": user_id,
            "redirect_uri": "http://localhost/seed/callback",
            "state": "seed",
        },
        follow_redirects=False,
    )
    if auth.status_code != 303:
        msg = f"instagram seed: /oauth/authorize returned {auth.status_code}: {auth.text[:200]}"
        raise RuntimeError(msg)
    code = query_param(auth.headers["location"], "code")

    token_resp = await client.post(
        "/oauth/access_token",
        data={"code": code, "grant_type": "authorization_code"},
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]
