"""Console entrypoint for ``python -m postpit``."""

import uvicorn

from postpit.config import get_settings


def main() -> None:
    """Run the postpit ASGI app under uvicorn using configured host/port."""
    settings = get_settings()
    uvicorn.run("postpit.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
