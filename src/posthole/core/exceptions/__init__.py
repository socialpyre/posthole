"""Application-wide exception types and the handlers that render them."""

from posthole.core.exceptions.handlers import handle_not_found
from posthole.core.exceptions.types import NotFoundError

__all__ = ["NotFoundError", "handle_not_found"]
