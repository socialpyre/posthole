"""Application-wide exceptions."""


class NotFoundError(Exception):
    """A resource was requested by id but no matching row exists.

    Carries ``resource`` (e.g. ``"post"``) and ``resource_id`` so the
    upstream handler can render resource-appropriate UI without parsing
    the message string.
    """

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} not found: {resource_id}")
        self.resource = resource
        self.resource_id = resource_id
