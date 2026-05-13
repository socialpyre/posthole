"""The :data:`PLATFORMS` tuple — every platform module the app mounts.

Lives in its own module (not ``__init__.py``) so the package init is purely
re-exports. Adding a platform = importing it here and appending to the tuple.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from posthole.platforms import instagram, tiktok

if TYPE_CHECKING:
    from posthole.platforms.types import Platform

PLATFORMS: tuple[Platform, ...] = (instagram, tiktok)
