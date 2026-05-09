import httpx


async def test_index_renders_hello(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "hello, postpit" in response.text


async def test_health_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/_health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
