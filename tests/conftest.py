"""Shared pytest fixtures for the posthole test suite."""

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio

from posthole.db import Database, get_db, oauth
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

    Routes read the database via ``Depends(get_db)`` — overridden here.
    Global exception handlers (which can't take ``Depends``) read from
    ``request.app.state.db`` — also overridden here so test DB visibility
    is consistent across both paths.
    """
    app.dependency_overrides[get_db] = lambda: db
    prior_state_db = getattr(app.state, "db", None)
    app.state.db = db

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        if prior_state_db is None:
            del app.state.db
        else:
            app.state.db = prior_state_db


@pytest.fixture
def ig_access_token(db: Database) -> str:
    """Short-lived IG token bound to the seeded test_studio account (178414000000001)."""
    return oauth.issue_token(db, account_id="178414000000001", kind="short").token
