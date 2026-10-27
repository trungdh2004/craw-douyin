from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.crawler import CrawlRunner
from douyin_crawler.models import CrawlLog, CrawlTarget


class CrawlLogResponse(BaseModel):
    id: int
    target_id: int | None
    target_name: str | None
    job_type: str
    trigger_type: str
    input_summary: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    status: str
    new_videos_count: int
    updated_videos_count: int
    error_message: str | None


class CrawlLogPage(BaseModel):
    items: list[CrawlLogResponse]
    total: int
    page: int
    page_size: int


def _to_response(log: CrawlLog, target_name: str | None) -> CrawlLogResponse:
    duration_ms: int | None = None
    if log.finished_at is not None and log.started_at is not None:
        duration_ms = max(
            0, int((log.finished_at - log.started_at).total_seconds() * 1000)
        )
    return CrawlLogResponse(
        id=log.id,
        target_id=log.target_id,
        target_name=target_name,
        job_type=log.job_type,
        trigger_type=log.trigger_type,
        input_summary=log.input_summary,
        started_at=log.started_at,
        finished_at=log.finished_at,
        duration_ms=duration_ms,
        status=log.status,
        new_videos_count=log.new_videos_count,
        updated_videos_count=log.updated_videos_count,
        error_message=log.error_message,
    )


def create_logs_router(
    sessions: async_sessionmaker[AsyncSession],
    crawl_runner: CrawlRunner,
) -> APIRouter:
    router = APIRouter(prefix="/api/logs", tags=["logs"])

    @router.get("")
    async def list_logs(
        job_type: str | None = None,
        status: str | None = None,
        target_id: int | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=200),
    ) -> CrawlLogPage:
        filters = []
        if job_type:
            filters.append(CrawlLog.job_type == job_type)
        if status:
            filters.append(CrawlLog.status == status)
        if target_id is not None:
            filters.append(CrawlLog.target_id == target_id)
        statement = (
            select(CrawlLog, CrawlTarget.name)
            .outerjoin(CrawlTarget, CrawlTarget.id == CrawlLog.target_id)
            .where(*filters)
            .order_by(CrawlLog.started_at.desc(), CrawlLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(CrawlLog).where(*filters)
        async with sessions() as session:
            total = await session.scalar(count_stmt) or 0
            rows = (await session.execute(statement)).all()
        items = [_to_response(log, name) for log, name in rows]
        return CrawlLogPage(items=items, total=total, page=page, page_size=page_size)

    @router.post("/{log_id}/retry", status_code=202)
    async def retry_log(log_id: int) -> dict[str, object]:
        async with sessions() as session:
            log = await session.get(CrawlLog, log_id)
            if log is None:
                raise HTTPException(status_code=404, detail="Crawl log not found")
            job_type = log.job_type
            target_id = log.target_id
            payload = dict(log.payload or {})
            summary = log.input_summary

            if job_type == "TARGET_CRAWL" and target_id is not None:
                crawl_runner.start(target_id, trigger_type="RETRY")
                return {"status": "ACCEPTED", "target_id": target_id}

            inputs = list(payload.get("inputs") or [])
            new_log = CrawlLog(
                target_id=None,
                job_type="SINGLE_CRAWL",
                trigger_type="RETRY",
                input_summary=summary,
                payload=payload,
                status="RUNNING",
            )
            session.add(new_log)
            await session.commit()
            await session.refresh(new_log)
            new_log_id = new_log.id

        crawl_runner.start_items(
            new_log_id,
            inputs,
            auto_download=bool(payload.get("auto_download", False)),
            is_bookmarked=bool(payload.get("is_bookmarked", False)),
            bookmark_collection=payload.get("bookmark_collection"),
        )
        return {"status": "ACCEPTED", "log_id": new_log_id}

    @router.delete("/{log_id}", status_code=204)
    async def delete_log(log_id: int) -> Response:
        async with sessions() as session:
            log = await session.get(CrawlLog, log_id)
            if log is None:
                raise HTTPException(status_code=404, detail="Crawl log not found")
            await session.delete(log)
            await session.commit()
        return Response(status_code=204)

    @router.delete("")
    async def clear_logs() -> dict[str, int]:
        async with sessions() as session:
            result = await session.execute(
                delete(CrawlLog).where(CrawlLog.status != "RUNNING")
            )
            await session.commit()
            deleted = int(getattr(result, "rowcount", 0) or 0)
        return {"deleted": deleted}

    return router
