from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from douyin_crawler.settings import get_settings


def create_database_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or get_settings().database_url, pool_pre_ping=True)
