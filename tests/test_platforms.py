"""Conformance tests for the :class:`posthole.platforms.types.Platform` Protocol.

Every entry in :data:`PLATFORMS` must expose the five module-level attributes
the Protocol declares. These tests run once per platform via parametrize, so
adding a new platform automatically gets its conformance checked. If a future
platform forgets `error_handler` or types `seed_flow` wrong, this test fails
fast at the unit level (before integration tests blow up confusingly).
"""

import inspect

import pytest
from fastapi import APIRouter

from posthole.platforms import PLATFORMS
from posthole.platforms.types import Platform


@pytest.mark.parametrize("plat", PLATFORMS, ids=lambda p: p.name)
def test_platform_satisfies_protocol(plat: Platform) -> None:
    """Each platform exposes name/router/error_type/error_handler/seed_flow."""
    assert isinstance(plat.name, str), "name must be a str"
    assert plat.name, "name must be non-empty"
    assert isinstance(plat.router, APIRouter), "router must be a FastAPI APIRouter"
    assert isinstance(plat.error_type, type), "error_type must be a class"
    assert issubclass(plat.error_type, Exception), "error_type must subclass Exception"
    assert callable(plat.error_handler), "error_handler must be callable"
    assert callable(plat.seed_flow), "seed_flow must be callable"


@pytest.mark.parametrize("plat", PLATFORMS, ids=lambda p: p.name)
def test_platform_seed_flow_is_coroutine_function(plat: Platform) -> None:
    """seed_flow is async (driven by the asyncio seed dispatcher)."""
    assert inspect.iscoroutinefunction(plat.seed_flow)


def test_platform_names_are_unique() -> None:
    """Two platforms sharing a name would collide in logs and any name-keyed dispatch."""
    names = [plat.name for plat in PLATFORMS]
    assert len(names) == len(set(names)), f"duplicate platform names: {names}"


@pytest.mark.parametrize("plat", PLATFORMS, ids=lambda p: p.name)
def test_platform_exception_handler_registered_on_app(plat: Platform) -> None:
    """``main.create_app()`` wires each platform's ``error_type`` to its ``error_handler``."""
    from posthole.main import app

    handler = app.exception_handlers.get(plat.error_type)
    assert handler is plat.error_handler, (
        f"{plat.name}: exception handler not registered on the real app — "
        f"check the platform loop in main.create_app()."
    )


@pytest.mark.parametrize("plat", PLATFORMS, ids=lambda p: p.name)
def test_platform_router_mounted_on_app(plat: Platform) -> None:
    """``main.create_app()`` includes each platform's router into the live app.

    We can't compare router objects (``include_router`` copies the routes
    into the app's own router tree). Instead, verify at least one route
    from the platform's router has a matching path on the app.
    """
    from posthole.main import app

    plat_paths = {getattr(r, "path", None) for r in plat.router.routes}
    plat_paths.discard(None)
    app_paths = {getattr(r, "path", None) for r in app.routes}
    overlap = plat_paths & app_paths
    assert overlap, (
        f"{plat.name}: none of its router paths ({sorted(plat_paths)}) appear on the app — "
        f"check the platform loop in main.create_app()."
    )
