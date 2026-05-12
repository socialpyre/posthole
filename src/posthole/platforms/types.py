"""Platform contract — the structural type every platform package satisfies.

Lives in its own module (not ``__init__.py``) so the package init is purely
re-exports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    import httpx
    from fastapi import APIRouter, FastAPI
    from fastapi_hotwire import HotwireTemplates


class PlatformModule(Protocol):
    """Structural type each platform package must expose at module scope.

    ``build_router``, ``seed_flow``, and ``install_exception_handlers`` are
    declared as :func:`staticmethod` so ty matches them against module-level
    ``def`` functions (which take no ``self``).

    Router-mounting contract (see :mod:`posthole.main`):

    - Routers may mount root-level single-segment wildcards (real API paths
      look like ``GET /{container_id}``). They mount AFTER the UI/system
      routers so literal admin paths win first-match resolution.
    - If two platforms would mount the same wildcard shape, the second one
      MUST namespace its route (e.g. ``/threads-containers/{id}``); silently
      relying on registration order is forbidden.

    Exception-handling contract:

    - ``install_exception_handlers(app)`` registers one or more FastAPI
      exception handlers that convert this platform's exception base
      (e.g. ``MetaAPIError``) into its wire envelope. ``main.py`` iterates
      ``PLATFORMS`` and calls this once per platform at app construction.
    """

    name: str

    @staticmethod
    def build_router(templates: HotwireTemplates) -> APIRouter: ...

    @staticmethod
    def seed_flow(client: httpx.AsyncClient) -> Awaitable[int]: ...

    @staticmethod
    def install_exception_handlers(app: FastAPI) -> None: ...
