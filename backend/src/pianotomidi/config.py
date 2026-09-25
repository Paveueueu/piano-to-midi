"""Settings from PIANOTOMIDI_* environment variables or .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PIANOTOMIDI_", env_file=".env", extra="ignore")

    # Browser origins allowed by CORS.
    cors_origins: list[str] = ["http://localhost:3300"]

    max_upload_mb: int = 50
    max_audio_minutes: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
