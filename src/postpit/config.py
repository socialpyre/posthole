"""Runtime configuration loaded from ``POSTPIT_*`` environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings; override any field via the ``POSTPIT_<NAME>`` env var."""

    model_config = SettingsConfigDict(env_prefix="POSTPIT_", extra="ignore")

    database_url: str = ":memory:"
    dev_reload: bool = False
    docs_enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5176


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance for this process."""
    return Settings()
