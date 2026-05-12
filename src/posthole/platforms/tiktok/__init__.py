"""TikTok interception — OAuth + content posting (video)."""

from posthole.platforms.tiktok.routes import build_router, install_exception_handlers, name
from posthole.platforms.tiktok.seed import seed_flow

__all__ = ["build_router", "install_exception_handlers", "name", "seed_flow"]
