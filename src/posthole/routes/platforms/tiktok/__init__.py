"""TikTok interception — OAuth + content posting (video).

Satisfies the :class:`posthole.routes.platforms.types.Platform` Protocol by
re-exporting ``name``, ``router``, ``error_type``, ``error_handler``,
and ``seed_flow``.
"""

from posthole.routes.platforms.tiktok.exceptions import TikTokAPIError, tiktok_exception_handler
from posthole.routes.platforms.tiktok.routes import router
from posthole.routes.platforms.tiktok.seed import seed_flow as _seed_flow_impl

# Platform Protocol attributes. Type information is structural via
# :class:`~posthole.routes.platforms.types.Platform`; we don't restate it
# here as annotations because that requires ``from __future__ import
# annotations`` to defer evaluation and adds a hidden coupling.
name = "tiktok"
error_type = TikTokAPIError
error_handler = tiktok_exception_handler
seed_flow = _seed_flow_impl

__all__ = ["error_handler", "error_type", "name", "router", "seed_flow"]
