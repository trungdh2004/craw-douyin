from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.crawler import CrawlRunner
from douyin_crawler.downloads import DownloadRunner
from douyin_crawler.models import CrawlLog, CrawlTarget, DouyinVideo


class CrawlLogEventItem(BaseModel):
    ts: str
    level: str
    step: str
    message: str


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
    scanned_count: int = 0
    target_limit: int = 0
    current_phase: str | None = None
    events: list[CrawlLogEventItem] = []
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
    payload = dict(log.payload or {})
    raw_events = payload.get("events") or []
    events: list[CrawlLogEventItem] = []
    for item in raw_events:
        if isinstance(item, dict):
            events.append(
                CrawlLogEventItem(
                    ts=str(item.get("ts") or ""),
                    level=str(item.get("level") or "INFO"),
                    step=str(item.get("step") or "STEP"),
                    message=str(item.get("message") or ""),
                )
            )
    scanned_count = int(
        payload.get("scanned_count")
        or (log.new_videos_count + log.updated_videos_count)
    )
    target_limit = int(payload.get("target_limit") or 0)
    current_phase = (
        str(payload["current_phase"]) if payload.get("current_phase") else None
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
        scanned_count=scanned_count,
        target_limit=target_limit,
        current_phase=current_phase,
        events=events,
        error_message=log.error_message,
    )


def create_logs_router(
    sessions: async_sessionmaker[AsyncSession],
    crawl_runner: CrawlRunner,
    download_runner: DownloadRunner | None = None,
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
            if job_type == "DOWNLOAD" and not items:
                dl_videos = list(
                    await session.scalars(
                        select(DouyinVideo)
                        .where(DouyinVideo.download_status == "COMPLETED")
                        .order_by(DouyinVideo.downloaded_at.desc())
                        .limit(page_size)
                    )
                )
                for idx, video in enumerate(dl_videos, start=1):
                    ts = video.downloaded_at or video.updated_at
                    items.append(
                        CrawlLogResponse(
                            id=-idx,
                            target_id=video.target_id,
                            target_name=video.author_nickname,
                            job_type="DOWNLOAD",
                            trigger_type="MANUAL",
                            input_summary=f"Tải media: {video.aweme_id}",
                            started_at=ts,
                            finished_at=ts,
                            duration_ms=0,
                            status="SUCCESS",
                            new_videos_count=0,
                            updated_videos_count=1,
                            error_message=None,
                        )
                    )
                total = len(items)
        return CrawlLogPage(items=items, total=total, page=page, page_size=page_size)

    @router.get("/{log_id}")
    async def get_log_detail(log_id: int) -> CrawlLogResponse:
        async with sessions() as session:
            row = (
                await session.execute(
                    select(CrawlLog, CrawlTarget.name)
                    .outerjoin(CrawlTarget, CrawlTarget.id == CrawlLog.target_id)
                    .where(CrawlLog.id == log_id)
                )
            ).first()
            if row is None:
                raise HTTPException(status_code=404, detail="Crawl log not found")
            log, name = row
            return _to_response(log, name)

    @router.post("/{log_id}/retry", status_code=202)
    async def retry_log(log_id: int) -> dict[str, object]:
        async with sessions() as session:
            log = await session.get(CrawlLog, log_id)
            if log is None:
                raise HTTPException(status_code=404, detail="Crawl log not found")
            if log.status not in ("FAILED", "CAPTCHA_BLOCKED"):
                raise HTTPException(
                    status_code=400,
                    detail="Only FAILED or CAPTCHA_BLOCKED logs can be retried",
                )
            job_type = log.job_type
            target_id = log.target_id
            payload = dict(log.payload or {})
            summary = log.input_summary

            if job_type == "TARGET_CRAWL" and target_id is not None:
                crawl_runner.start(target_id, trigger_type="RETRY")
                return {"status": "ACCEPTED", "target_id": target_id}

            if job_type == "DOWNLOAD":
                aweme_id = str(payload.get("aweme_id") or "")
                if not aweme_id or download_runner is None:
                    raise HTTPException(status_code=400, detail="Missing aweme_id for download retry")
                await download_runner.start(aweme_id, trigger_type="RETRY", record_log=True)
                return {"status": "ACCEPTED", "aweme_id": aweme_id}

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
                delete(CrawlLog).where(
                    CrawlLog.status.in_(["SUCCESS", "FAILED", "CAPTCHA_BLOCKED"])
                )
            )
            await session.commit()
            deleted = int(getattr(result, "rowcount", 0) or 0)
        return {"deleted": deleted}

    return router
