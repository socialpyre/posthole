"""Posts-page exceptions."""

from posthole.core.exceptions import NotFoundError


class PostNotFoundError(NotFoundError):
    """``/posts/{id}`` was requested for an id with no matching row."""

    def __init__(self, post_id: str) -> None:
        super().__init__(resource="post", resource_id=post_id)
