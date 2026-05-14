"""Aggregated router for the whole app.

Combines every page + platform router into one :class:`APIRouter` that
:mod:`posthole.main` can mount with a single ``app.include_router(router)``
call. Include order matters and is encoded here, not in ``main``.
"""

from fastapi import APIRouter

from posthole.routes.pages.accounts.routes import router as _accounts_router
from posthole.routes.pages.health.routes import router as _health_router
from posthole.routes.pages.posts.routes import router as _inbox_router
from posthole.routes.pages.scenarios.routes import router as _scenarios_router
from posthole.routes.pages.settings.routes import router as _settings_router
from posthole.routes.platforms import PLATFORMS

router = APIRouter()

router.include_router(_inbox_router)
router.include_router(_accounts_router)
router.include_router(_scenarios_router)
router.include_router(_settings_router)
router.include_router(_health_router)

for _plat in PLATFORMS:
    router.include_router(_plat.router)

__all__ = ["router"]
