def main() -> None:
    import uvicorn

    from postpit.config import get_settings

    settings = get_settings()
    uvicorn.run("postpit.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
