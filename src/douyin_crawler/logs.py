from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.models import CrawlLog, CrawlTarget


class CrawlLogResponse(BaseModel):
    id: int
    target_id: int | None
    target_name: str | None
    started_at: datetime
    finished_at: datetime | None
    status: str
    new_videos_count: int
    updated_videos_count: int
    error_message: str | None


def create_logs_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(prefix="/api/logs", tags=["logs"])

    @router.get("")
    async def list_logs(limit: int = Query(default=50, ge=1, le=200)) -> list[CrawlLogResponse]:
        statement = (
            select(CrawlLog, CrawlTarget.name)
            .outerjoin(CrawlTarget, CrawlTarget.id == CrawlLog.target_id)
            .order_by(CrawlLog.started_at.desc(), CrawlLog.id.desc())
            .limit(limit)
        )
        async with sessions() as session:
            rows = (await session.execute(statement)).all()
        return [
            CrawlLogResponse(
                id=log.id, target_id=log.target_id, target_name=name,
                started_at=log.started_at, finished_at=log.finished_at,
                status=log.status, new_videos_count=log.new_videos_count,
                updated_videos_count=log.updated_videos_count,
                error_message=log.error_message,
            )
            for log, name in rows
        ]

    return router
