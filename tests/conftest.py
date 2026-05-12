"""Shared pytest fixtures for the posthole test suite."""

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio

from posthole.db import Database, get_db
from posthole.main import app


@pytest.fixture
def db() -> Iterator[Database]:
    """Fresh in-memory ``Database`` per test, with migrations applied."""
    d = Database(":memory:")

    try:
        yield d
    finally:
        d.close()


@pytest_asyncio.fixture
async def client(db: Database) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an httpx ``AsyncClient`` whose routes see the per-test ``db``.

    Routes must read the database via ``Depends(get_db)``; direct
    ``request.app.state.db`` access bypasses this override and would land on
    whatever DB the real lifespan opened from ``POSTHOLE_DATABASE_URL``.
    """
    app.dependency_overrides[get_db] = lambda: db

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def ig_access_token(db: Database) -> str:
    """Short-lived IG token bound to the seeded test_studio account (178414000000001)."""
    return db.oauth.issue_token(account_id="178414000000001", kind="short").token
