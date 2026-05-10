"""Console entrypoint for ``python -m posthole``."""

import uvicorn

from posthole.config import get_settings


def main() -> None:
    """Run the posthole ASGI app under uvicorn using configured host/port."""
    settings = get_settings()
    uvicorn.run("posthole.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
