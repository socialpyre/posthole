"""Instagram interception — OAuth + publishing."""

from posthole.platforms.instagram.routes import build_router, name
from posthole.platforms.instagram.seed import seed_flow

__all__ = ["build_router", "name", "seed_flow"]
