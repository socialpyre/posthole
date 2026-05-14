"""Platform contract — the structural type every platform package satisfies.

Lives in its own module (not ``__init__.py``) so the package init is purely
re-exports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import httpx
    from fastapi import APIRouter


class Platform(Protocol):
    """Structural type each platform package must expose at module scope.

    Describes what a platform IS (domain), not what ``main.py`` happens to
    call (wiring). Four attributes + a name:

    Router-mounting contract (see :mod:`posthole.main`):

    - Routers may mount root-level single-segment wildcards (real API paths
      look like ``GET /{container_id}``). They mount AFTER the UI/system
      routers so literal admin paths win first-match resolution.
    - If two platforms would mount the same wildcard shape, the second one
      MUST namespace its route (e.g. ``/threads-containers/{id}``); silently
      relying on registration order is forbidden.

    Exception-handling contract:

    - ``error_type`` is the base class for this platform's API errors;
      handlers ``raise`` it (or subclasses) and ``error_handler`` converts
      to the wire envelope. ``main.py`` registers ``error_handler`` against
      ``error_type`` via ``app.add_exception_handler`` once per platform.

    Seed contract:

    - ``seed_flow(client)`` drives this platform's seed-data flow over HTTP
      loopback. Called from :mod:`posthole.seed` once per platform.
    """

    # Declared as read-only properties so each member is covariant in its
    # return type. Plain Protocol attributes are invariant, which fails
    # when modules assign narrower concrete values (e.g. ``type[Subclass]``
    # to ``type[Exception]``). Modules can't reassign these at runtime
    # anyway, so read-only is the honest shape.
    @property
    def name(self) -> str: ...
    @property
    def router(self) -> APIRouter: ...
    @property
    def error_type(self) -> type[Exception]: ...
    @property
    def seed_flow(self) -> Callable[[httpx.AsyncClient], Awaitable[int]]: ...
    # FastAPI's add_exception_handler is typed Callable[..., Any]; we
    # match that here rather than the stricter (Request, Exception) ->
    # Awaitable[Response] form so platforms can return any Response
    # subclass (JSONResponse, HTMLResponse, ...) without variance hassles.
    @property
    def error_handler(self) -> Callable[..., Any]: ...
