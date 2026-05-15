"""Tests for the CSRF origin/referer guard middleware."""

import httpx


async def test_csrf_blocks_cross_origin_post(client: httpx.AsyncClient) -> None:
    """A POST with an ``Origin`` that doesn't match the host returns 403."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "fine",
            "display_name": "Fine",
            "account_type": "BUSINESS",
        },
        headers={"Origin": "http://evil.example"},
    )

    assert response.status_code == 403
    assert "CSRF" in response.text


async def test_csrf_blocks_cross_origin_referer_only(client: httpx.AsyncClient) -> None:
    """No ``Origin`` but a mismatched ``Referer`` is also blocked.

    Old browsers and some form submissions only send ``Referer``; the
    middleware still has to recognize the cross-origin case.
    """
    response = await client.post(
        "/accounts/some-id/delete",
        headers={"Referer": "http://evil.example/page"},
    )

    assert response.status_code == 403


async def test_csrf_allows_same_origin_post(client: httpx.AsyncClient) -> None:
    """A POST whose ``Origin`` matches the request host passes through."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "newco",
            "display_name": "New Co",
            "account_type": "BUSINESS",
        },
        headers={"Origin": "http://test"},
        follow_redirects=False,
    )

    assert response.status_code == 303


async def test_csrf_allows_missing_headers(client: httpx.AsyncClient) -> None:
    """No ``Origin`` and no ``Referer`` (curl, IDE tools) is allowed.

    The threat model targets browsers, which always send one or both for
    cross-origin writes. Bare tooling stays usable.
    """
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "barecurl",
            "display_name": "Bare Curl",
            "account_type": "BUSINESS",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


async def test_csrf_blocks_unsafe_method_with_empty_host(client: httpx.AsyncClient) -> None:
    """Missing/empty Host on an unsafe method is rejected — Host is mandatory in HTTP/1.1."""
    response = await client.post(
        "/accounts/new",
        data={
            "platform": "instagram",
            "username": "x",
            "display_name": "X",
            "account_type": "BUSINESS",
        },
        headers={"Host": ""},
    )

    assert response.status_code == 403


async def test_csrf_does_not_block_safe_methods(client: httpx.AsyncClient) -> None:
    """GET is never guarded — read endpoints stay open regardless of Origin."""
    response = await client.get(
        "/accounts",
        headers={"Origin": "http://evil.example"},
    )

    assert response.status_code == 200
