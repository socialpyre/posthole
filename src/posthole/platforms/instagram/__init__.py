"""Instagram interception — OAuth + publishing."""

from posthole.platforms.instagram.routes import build_router, install_exception_handlers, name
from posthole.platforms.instagram.seed import seed_flow

__all__ = ["build_router", "install_exception_handlers", "name", "seed_flow"]
