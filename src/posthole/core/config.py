"""Runtime configuration loaded from ``POSTHOLE_*`` environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["console", "json"]


class Settings(BaseSettings):
    """Process-wide settings; override any field via the ``POSTHOLE_<NAME>`` env var."""

    model_config = SettingsConfigDict(env_prefix="POSTHOLE_", extra="ignore")

    database_url: str = "./posthole.db"
    dev_reload: bool = False
    docs_enabled: bool = True
    environment: str = "local"
    host: str = "127.0.0.1"
    log_format: LogFormat = "console"
    log_level: LogLevel = "DEBUG"
    port: int = 5176


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance for this process."""
    return Settings()
