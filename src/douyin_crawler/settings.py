from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://douyin:douyin@localhost:5432/douyin"
    browser_profile_directory: Path = Path("browser-profile")
    covers_directory: Path = Path("covers")
    downloads_directory: Path = Path("downloads")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
