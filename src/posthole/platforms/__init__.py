"""Per-platform mock interception.

Public surface (re-exported here):

- :class:`PlatformModule` — the structural contract every platform satisfies
  (defined in :mod:`posthole.platforms.types`).
- :data:`PLATFORMS` — the registered platform modules
  (defined in :mod:`posthole.platforms.registry`).
- :func:`query_param` — cross-platform URL helper used by seed flows
  (defined in :mod:`posthole.platforms.helpers`).
"""

from posthole.platforms.helpers import query_param
from posthole.platforms.registry import PLATFORMS
from posthole.platforms.types import PlatformModule

__all__ = ["PLATFORMS", "PlatformModule", "query_param"]
