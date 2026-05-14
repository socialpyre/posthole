"""Tests for the Instagram publishing flow — container, status, publish."""

import httpx

ALICE = "178414000000001"  # test_studio, seeded by migration 0001


async def test_create_container_returns_id(client: httpx.AsyncClient, ig_access_token: str) -> None:
    response = await client.post(
        f"/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"image_url": "https://img/1.jpg", "caption": "hi"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["id"].startswith("mock-container-")


async def test_create_container_requires_image_url(
    client: httpx.AsyncClient, ig_access_token: str
) -> None:
    response = await client.post(
        f"/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"caption": "no image"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["error_subcode"] == 2207001


async def test_create_container_rejects_unsupported_media_type(
    client: httpx.AsyncClient, ig_access_token: str
) -> None:
    """Phase 1 supports IMAGE only; VIDEO / REELS / CAROUSEL come later."""
    response = await client.post(
        f"/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"image_url": "https://img/1.jpg", "media_type": "VIDEO"},
    )

    assert response.status_code == 400


async def test_create_container_without_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"/{ALICE}/media",
        data={"image_url": "https://img/1.jpg"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == 190


async def test_create_container_with_unknown_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"/{ALICE}/media",
        params={"access_token": "mock-short-not-a-real-token"},
        data={"image_url": "https://img/1.jpg"},
    )

    assert response.status_code == 401


async def test_container_status_finished(client: httpx.AsyncClient, ig_access_token: str) -> None:
    container = await client.post(
        f"/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"image_url": "https://img/1.jpg"},
    )
    container_id = container.json()["id"]

    status = await client.get(f"/{container_id}", params={"access_token": ig_access_token})

    body = status.json()
    assert status.status_code == 200
    assert body["status_code"] == "FINISHED"
    assert body["media_type"] == "IMAGE"
    assert body["media_product_type"] == "FEED"


async def test_container_status_unknown_returns_404(
    client: httpx.AsyncClient, ig_access_token: str
) -> None:
    response = await client.get(
        "/mock-container-does-not-exist", params={"access_token": ig_access_token}
    )

    assert response.status_code == 404


async def test_container_status_without_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/mock-container-anything")

    assert response.status_code == 401


async def test_publish_marks_post_published(
    client: httpx.AsyncClient, ig_access_token: str
) -> None:
    container = await client.post(
        f"/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"image_url": "https://img/1.jpg", "caption": "go live"},
    )
    container_id = container.json()["id"]

    publish = await client.post(
        f"/{ALICE}/media_publish",
        params={"access_token": ig_access_token},
        data={"creation_id": container_id},
    )

    body = publish.json()
    assert publish.status_code == 200
    assert body["id"].startswith("mock-post-")


async def test_publish_unknown_container_returns_404(
    client: httpx.AsyncClient, ig_access_token: str
) -> None:
    response = await client.post(
        f"/{ALICE}/media_publish",
        params={"access_token": ig_access_token},
        data={"creation_id": "mock-container-nope"},
    )

    assert response.status_code == 404


async def test_publish_without_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"/{ALICE}/media_publish",
        data={"creation_id": "mock-container-anything"},
    )

    assert response.status_code == 401


async def test_api_version_prefix_stripped(client: httpx.AsyncClient, ig_access_token: str) -> None:
    """``/v22.0/{user_id}/media`` should resolve to the bare publishing route."""
    response = await client.post(
        f"/v22.0/{ALICE}/media",
        params={"access_token": ig_access_token},
        data={"image_url": "https://img/v22.jpg", "caption": "via versioned URL"},
    )

    assert response.status_code == 200
    assert response.json()["id"].startswith("mock-container-")
