"""Instagram interception — OAuth + publishing.

Satisfies the :class:`posthole.platforms.types.Platform` Protocol by
re-exporting ``name``, ``router``, ``error_type``, ``error_handler``,
and ``seed_flow``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.platforms.instagram.exceptions import MetaAPIError, meta_exception_handler
from posthole.platforms.instagram.routes import router
from posthole.platforms.instagram.seed import seed_flow as _seed_flow_impl

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any

    import httpx

name: str = "instagram"
error_type: type[Exception] = MetaAPIError
error_handler: Callable[..., Any] = meta_exception_handler
seed_flow: Callable[[httpx.AsyncClient], Awaitable[int]] = _seed_flow_impl

__all__ = ["error_handler", "error_type", "name", "router", "seed_flow"]
