"""Tests for the TikTok publishing flow — init, chunked PUT, status fetch."""

from urllib.parse import parse_qs, urlparse

import httpx

CREATOR = "tt-7000000000000000001"


async def _bearer(client: httpx.AsyncClient) -> str:
    auth = await client.post(
        "/auth/authorize/",
        data={"account_id": CREATOR, "redirect_uri": "http://localhost/cb", "state": ""},
        follow_redirects=False,
    )
    code = parse_qs(urlparse(auth.headers["location"]).query)["code"][0]
    token = await client.post(
        "/oauth/token/",
        data={"code": code, "grant_type": "authorization_code"},
    )
    return token.json()["access_token"]


async def test_init_pull_from_url(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)

    response = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {"title": "hi", "privacy_level": "SELF_ONLY"},
            "source_info": {"source": "PULL_FROM_URL", "video_url": "https://video/x.mp4"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["error"]["code"] == "ok"
    assert body["data"]["publish_id"].startswith("v_pub_")
    # PULL_FROM_URL doesn't get an upload_url
    assert "upload_url" not in body["data"]


async def test_init_file_upload_returns_upload_url(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)

    response = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {"title": "uploaded"},
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 1024,
                "chunk_size": 1024,
                "total_chunk_count": 1,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["publish_id"].startswith("v_pub_")
    assert body["data"]["upload_url"].endswith(f"/upload/{body['data']['publish_id']}")


async def test_init_rejects_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/post/publish/video/init/",
        json={"post_info": {}, "source_info": {"source": "PULL_FROM_URL", "video_url": "x"}},
    )

    assert response.status_code == 401


async def test_init_rejects_bad_source(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)

    response = await client.post(
        "/post/publish/video/init/",
        json={"post_info": {}, "source_info": {"source": "MAGIC"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_param"


async def test_put_chunk_accepts_bytes(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)
    init = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {},
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 4,
                "chunk_size": 4,
                "total_chunk_count": 1,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    publish_id = init.json()["data"]["publish_id"]

    response = await client.put(
        f"/upload/{publish_id}",
        content=b"\x00\x01\x02\x03",
        headers={"Content-Range": "bytes 0-3/4", "Content-Type": "video/mp4"},
    )

    assert response.status_code == 200


async def test_put_chunk_rejects_missing_content_range(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)
    init = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {},
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 4,
                "chunk_size": 4,
                "total_chunk_count": 1,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    publish_id = init.json()["data"]["publish_id"]

    response = await client.put(f"/upload/{publish_id}", content=b"abcd")

    assert response.status_code == 400


async def test_put_chunk_unknown_publish_id(client: httpx.AsyncClient) -> None:
    response = await client.put(
        "/upload/v_pub_does_not_exist",
        content=b"x",
        headers={"Content-Range": "bytes 0-0/1"},
    )

    assert response.status_code == 404


async def test_status_fetch_flips_to_published(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)
    init = await client.post(
        "/post/publish/video/init/",
        json={
            "post_info": {"title": "hello"},
            "source_info": {"source": "PULL_FROM_URL", "video_url": "https://video/x.mp4"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    publish_id = init.json()["data"]["publish_id"]

    response = await client.post(
        "/post/publish/status/fetch/",
        json={"publish_id": publish_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["status"] == "PUBLISH_COMPLETE"
    # Mirroring TikTok's actual schema typo:
    assert "publicaly_available_post_id" in body["data"]
    assert len(body["data"]["publicaly_available_post_id"]) == 1


async def test_status_fetch_unknown_publish_id(client: httpx.AsyncClient) -> None:
    token = await _bearer(client)

    response = await client.post(
        "/post/publish/status/fetch/",
        json={"publish_id": "v_pub_nope"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


async def test_status_fetch_rejects_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/post/publish/status/fetch/",
        json={"publish_id": "v_pub_anything"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "access_token_invalid"


async def test_versioned_url_strip(client: httpx.AsyncClient) -> None:
    """``/v2/post/publish/video/init/`` resolves to the same handler as the stripped path."""
    token = await _bearer(client)

    response = await client.post(
        "/v2/post/publish/video/init/",
        json={
            "post_info": {"title": "via versioned URL"},
            "source_info": {"source": "PULL_FROM_URL", "video_url": "https://v/x.mp4"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["publish_id"].startswith("v_pub_")
