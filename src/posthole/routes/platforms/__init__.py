"""Per-platform mock interception.

Public surface (re-exported here):

- :class:`Platform` — the structural contract every platform satisfies
  (defined in :mod:`posthole.routes.platforms.types`).
- :data:`PLATFORMS` — the registered platform modules
  (defined in :mod:`posthole.routes.platforms.registry`).
- :class:`VersionStripMiddleware` — strip ``/v22.0/...`` style version
  prefixes from request paths (defined in
  :mod:`posthole.routes.platforms.middleware`).
- :func:`query_param` — cross-platform URL helper used by seed flows
  (defined in :mod:`posthole.routes.platforms.helpers`).
"""

from posthole.routes.platforms.helpers import query_param
from posthole.routes.platforms.middleware import VersionStripMiddleware
from posthole.routes.platforms.registry import PLATFORMS
from posthole.routes.platforms.types import Platform

__all__ = [
    "PLATFORMS",
    "Platform",
    "VersionStripMiddleware",
    "query_param",
]
