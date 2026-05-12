"""TikTok interception — OAuth + content posting (video)."""

from posthole.platforms.tiktok.routes import build_router, name
from posthole.platforms.tiktok.seed import seed_flow

__all__ = ["build_router", "name", "seed_flow"]
