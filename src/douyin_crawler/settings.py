from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://douyin:douyin@localhost:5432/douyin"
    browser_profile_directory: Path = Path("browser-profile")
    covers_directory: Path = Path("covers")
    downloads_directory: Path = Path("downloads")
    edit_douyin_url: str = "http://127.0.0.1:8000"
    edit_douyin_directory: Path = Path("/home/trungdh/dev/tools/edit-douyin")
    admin_username: str = "admin"
    admin_password: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
