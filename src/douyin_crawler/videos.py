from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.models import CrawlTarget, DouyinVideo


class VideoResponse(BaseModel):
    aweme_id: str
    target_id: int | None
    source_name: str | None
    aweme_type: int
    description: str
    hashtags: list[str]
    create_time: datetime
    author_nickname: str
    digg_count: int
    comment_count: int
    share_count: int
    collect_count: int
    cover_url: str | None
    original_url: str
    download_status: str
    video_local_path: str | None


class VideoPage(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


SORT_COLUMNS = {
    "create_time": DouyinVideo.create_time,
    "crawled_at": DouyinVideo.crawled_at,
    "digg_count": DouyinVideo.digg_count,
    "share_count": DouyinVideo.share_count,
    "comment_count": DouyinVideo.comment_count,
    "collect_count": DouyinVideo.collect_count,
}


def create_videos_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(prefix="/api/videos", tags=["videos"])

    @router.get("")
    async def list_videos(
        target_id: int | None = None,
        search: str | None = None,
        min_digg: int | None = Query(default=None, ge=0),
        download_status: Literal["NONE", "DOWNLOADING", "COMPLETED", "FAILED"] | None = None,
        aweme_type: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: Literal["create_time", "crawled_at", "digg_count", "share_count", "comment_count", "collect_count"] = "create_time",
        order: Literal["asc", "desc"] = "desc",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=24, ge=1, le=100),
    ) -> VideoPage:
        statement = select(DouyinVideo, CrawlTarget.name).outerjoin(
            CrawlTarget, CrawlTarget.id == DouyinVideo.target_id
        )
        if target_id is not None:
            statement = statement.where(DouyinVideo.target_id == target_id)
        if search:
            statement = statement.where(DouyinVideo.description.ilike(f"%{search}%"))
        if min_digg is not None:
            statement = statement.where(DouyinVideo.digg_count >= min_digg)
        if download_status:
            statement = statement.where(DouyinVideo.download_status == download_status)
        if aweme_type is not None:
            statement = statement.where(DouyinVideo.aweme_type == aweme_type)
        if date_from:
            statement = statement.where(DouyinVideo.create_time >= date_from)
        if date_to:
            statement = statement.where(DouyinVideo.create_time <= date_to)
        async with sessions() as session:
            total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
            sort_column = SORT_COLUMNS[sort]
            direction = sort_column.asc() if order == "asc" else sort_column.desc()
            rows = (await session.execute(statement.order_by(direction, DouyinVideo.aweme_id).offset((page - 1) * page_size).limit(page_size))).all()
        return VideoPage(
            items=[_response(video, source) for video, source in rows],
            total=total, page=page, page_size=page_size,
        )

    @router.get("/{aweme_id}/cover")
    async def local_cover(aweme_id: str) -> FileResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if video is None or not video.cover_local_path or not Path(video.cover_local_path).is_file():
            raise HTTPException(status_code=404, detail="Cover not found")
        return FileResponse(video.cover_local_path)

    return router


def _response(video: DouyinVideo, source_name: str | None) -> VideoResponse:
    return VideoResponse(
        aweme_id=video.aweme_id, target_id=video.target_id, source_name=source_name,
        aweme_type=video.aweme_type, description=video.description, hashtags=video.hashtags,
        create_time=video.create_time, author_nickname=video.author_nickname,
        digg_count=video.digg_count, comment_count=video.comment_count,
        share_count=video.share_count, collect_count=video.collect_count,
        cover_url=f"/api/videos/{video.aweme_id}/cover" if video.cover_local_path else None,
        original_url=f"https://www.douyin.com/video/{video.aweme_id}",
        download_status=video.download_status, video_local_path=video.video_local_path,
    )
