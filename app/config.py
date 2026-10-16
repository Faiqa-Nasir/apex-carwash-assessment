"""Settings loaded from the environment or a .env file. No secrets in code."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    api_token: str


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them for every request."""
    return Settings()
