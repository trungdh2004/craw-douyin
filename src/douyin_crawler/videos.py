from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.models import CrawlTarget, DouyinVideo, VideoSource
from douyin_crawler.targets import TargetCreate, TargetService, TargetType

SortField = Literal[
    "create_time",
    "crawled_at",
    "digg_count",
    "share_count",
    "comment_count",
    "collect_count",
    "duration_ms",
]


class VideoResponse(BaseModel):
    aweme_id: str
    target_id: int | None
    source_names: list[str]
    aweme_type: int
    description: str
    hashtags: list[str]
    create_time: datetime
    crawled_at: datetime
    author_sec_uid: str
    author_nickname: str
    author_avatar: str | None
    digg_count: int
    comment_count: int
    share_count: int
    collect_count: int
    duration_ms: int
    width: int | None
    height: int | None
    music_title: str | None
    music_author: str | None
    image_count: int
    cover_url: str | None
    original_url: str
    download_status: str
    video_local_path: str | None
    downloaded_at: datetime | None
    download_error: str | None
    is_bookmarked: bool
    bookmarked_at: datetime | None
    bookmark_collection: str | None
    bookmark_note: str | None


class VideoPage(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


class BookmarkPatchRequest(BaseModel):
    is_bookmarked: bool
    bookmark_collection: str | None = None
    bookmark_note: str | None = None


class BatchBookmarkRequest(BaseModel):
    aweme_ids: list[str] = Field(min_length=1, max_length=200)
    is_bookmarked: bool = True
    bookmark_collection: str | None = None


class BookmarkCollectionSummary(BaseModel):
    name: str
    count: int


SORT_COLUMNS = {
    "create_time": DouyinVideo.create_time,
    "crawled_at": DouyinVideo.crawled_at,
    "digg_count": DouyinVideo.digg_count,
    "share_count": DouyinVideo.share_count,
    "comment_count": DouyinVideo.comment_count,
    "collect_count": DouyinVideo.collect_count,
    "duration_ms": DouyinVideo.duration_ms,
}


def create_videos_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(prefix="/api/videos", tags=["videos"])

    @router.get("")
    async def list_videos(
        target_id: int | None = None,
        search: str | None = None,
        min_digg: int | None = Query(default=None, ge=0),
        min_duration_ms: int | None = Query(default=None, ge=0),
        max_duration_ms: int | None = Query(default=None, ge=0),
        download_status: Literal["NONE", "DOWNLOADING", "COMPLETED", "FAILED"] | None = None,
        aweme_type: int | None = None,
        is_bookmarked: bool | None = None,
        bookmark_collection: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        crawled_from: datetime | None = None,
        crawled_to: datetime | None = None,
        sort: SortField = "create_time",
        order: Literal["asc", "desc"] = "desc",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=24, ge=1, le=100),
    ) -> VideoPage:
        statement = select(DouyinVideo)
        if target_id is not None:
            statement = statement.where(
                select(VideoSource.aweme_id)
                .where(
                    VideoSource.aweme_id == DouyinVideo.aweme_id,
                    VideoSource.target_id == target_id,
                )
                .exists()
            )
        if search:
            statement = statement.where(DouyinVideo.description.ilike(f"%{search}%"))
        if min_digg is not None:
            statement = statement.where(DouyinVideo.digg_count >= min_digg)
        if min_duration_ms is not None:
            statement = statement.where(DouyinVideo.duration_ms >= min_duration_ms)
        if max_duration_ms is not None:
            statement = statement.where(DouyinVideo.duration_ms <= max_duration_ms)
        if download_status:
            statement = statement.where(DouyinVideo.download_status == download_status)
        if aweme_type is not None:
            statement = statement.where(DouyinVideo.aweme_type == aweme_type)
        if is_bookmarked is not None:
            statement = statement.where(DouyinVideo.is_bookmarked.is_(is_bookmarked))
        if bookmark_collection:
            statement = statement.where(DouyinVideo.bookmark_collection == bookmark_collection)
        if date_from:
            statement = statement.where(DouyinVideo.create_time >= date_from)
        if date_to:
            statement = statement.where(DouyinVideo.create_time <= date_to)
        if crawled_from:
            statement = statement.where(DouyinVideo.crawled_at >= crawled_from)
        if crawled_to:
            statement = statement.where(DouyinVideo.crawled_at <= crawled_to)
        async with sessions() as session:
            total = (
                await session.scalar(select(func.count()).select_from(statement.subquery()))
                or 0
            )
            sort_column = SORT_COLUMNS[sort]
            direction = sort_column.asc() if order == "asc" else sort_column.desc()
            videos = list(
                await session.scalars(
                    statement.order_by(direction, DouyinVideo.aweme_id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            source_rows = (
                (
                    await session.execute(
                        select(VideoSource.aweme_id, CrawlTarget.name)
                        .join(CrawlTarget, CrawlTarget.id == VideoSource.target_id)
                        .where(VideoSource.aweme_id.in_([video.aweme_id for video in videos]))
                    )
                ).all()
                if videos
                else []
            )
        source_names: dict[str, list[str]] = {}
        for aweme_id, name in source_rows:
            source_names.setdefault(aweme_id, []).append(name)
        return VideoPage(
            items=[_response(video, source_names.get(video.aweme_id, [])) for video in videos],
            total=total,
            page=page,
            page_size=page_size,
        )

    @router.get("/{aweme_id}/cover")
    async def local_cover(aweme_id: str) -> FileResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if (
            video is None
            or not video.cover_local_path
            or not Path(video.cover_local_path).is_file()
        ):
            raise HTTPException(status_code=404, detail="Cover not found")
        return FileResponse(video.cover_local_path)

    @router.get("/{aweme_id}/stream")
    async def stream_video(aweme_id: str) -> FileResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if (
            video is None
            or not video.video_local_path
            or not Path(video.video_local_path).is_file()
        ):
            raise HTTPException(status_code=404, detail="Local video file not found")
        return FileResponse(video.video_local_path, media_type="video/mp4")

    @router.get("/{aweme_id}/images/{index}")
    async def stream_album_image(aweme_id: str, index: int) -> FileResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if video is None or not video.video_local_path:
            raise HTTPException(status_code=404, detail="Local album folder not found")
        image_path = Path(video.video_local_path) / f"{index:02}.jpg"
        if not image_path.is_file():
            raise HTTPException(status_code=404, detail="Album image not found")
        return FileResponse(image_path, media_type="image/jpeg")

    @router.patch("/{aweme_id}/bookmark")
    async def update_bookmark(
        aweme_id: str, payload: BookmarkPatchRequest
    ) -> VideoResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if video is None:
                raise HTTPException(status_code=404, detail="Douyin post not found")
            video.is_bookmarked = payload.is_bookmarked
            if payload.is_bookmarked:
                if video.bookmarked_at is None:
                    video.bookmarked_at = datetime.now(UTC)
                if payload.bookmark_collection is not None:
                    video.bookmark_collection = payload.bookmark_collection or None
                if payload.bookmark_note is not None:
                    video.bookmark_note = payload.bookmark_note
            else:
                video.bookmarked_at = None
                if payload.bookmark_collection is not None:
                    video.bookmark_collection = payload.bookmark_collection or None
                if payload.bookmark_note is not None:
                    video.bookmark_note = payload.bookmark_note
            video.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(video)
            source_rows = (
                await session.execute(
                    select(CrawlTarget.name)
                    .join(VideoSource, CrawlTarget.id == VideoSource.target_id)
                    .where(VideoSource.aweme_id == aweme_id)
                )
            ).scalars().all()
            return _response(video, list(source_rows))

    @router.post("/batch-bookmark")
    async def batch_bookmark(payload: BatchBookmarkRequest) -> dict[str, int]:
        updated = 0
        now = datetime.now(UTC)
        async with sessions() as session:
            videos = list(
                await session.scalars(
                    select(DouyinVideo).where(
                        DouyinVideo.aweme_id.in_(list(dict.fromkeys(payload.aweme_ids)))
                    )
                )
            )
            for video in videos:
                video.is_bookmarked = payload.is_bookmarked
                video.bookmarked_at = now if payload.is_bookmarked else None
                if payload.bookmark_collection is not None:
                    video.bookmark_collection = payload.bookmark_collection or None
                video.updated_at = now
                updated += 1
            await session.commit()
        return {"updated": updated}

    return router


def create_bookmarks_router(
    sessions: async_sessionmaker[AsyncSession],
    target_service: TargetService,
) -> APIRouter:
    router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])

    @router.get("/collections")
    async def list_collections() -> list[BookmarkCollectionSummary]:
        async with sessions() as session:
            rows = (
                await session.execute(
                    select(DouyinVideo.bookmark_collection, func.count())
                    .where(
                        DouyinVideo.is_bookmarked.is_(True),
                        DouyinVideo.bookmark_collection.is_not(None),
                        DouyinVideo.bookmark_collection != "",
                    )
                    .group_by(DouyinVideo.bookmark_collection)
                    .order_by(func.count().desc(), DouyinVideo.bookmark_collection.asc())
                )
            ).all()
        return [
            BookmarkCollectionSummary(name=str(name), count=int(count))
            for name, count in rows
            if name
        ]

    @router.post("/sync-douyin", status_code=202)
    async def sync_douyin_collect() -> dict[str, object]:
        async with sessions() as session:
            target = await session.scalar(
                select(CrawlTarget)
                .where(CrawlTarget.target_type == TargetType.COLLECT.value)
                .order_by(CrawlTarget.id.asc())
            )
        if target is None:
            created = await target_service.create(
                TargetCreate(
                    name="Đã lưu trên Douyin",
                    target_type=TargetType.COLLECT,
                    target_value="self",
                    cron_expr="0 */6 * * *",
                    max_items_per_run=50,
                    is_active=True,
                )
            )
            target_id = created.id
        else:
            target_id = target.id
        await target_service.run_now(target_id)
        return {"status": "ACCEPTED", "target_id": target_id}

    return router


def _response(video: DouyinVideo, source_names: list[str]) -> VideoResponse:
    return VideoResponse(
        aweme_id=video.aweme_id,
        target_id=video.target_id,
        source_names=source_names,
        aweme_type=video.aweme_type,
        description=video.description,
        hashtags=video.hashtags,
        create_time=video.create_time,
        crawled_at=video.crawled_at,
        author_sec_uid=video.author_sec_uid,
        author_nickname=video.author_nickname,
        author_avatar=video.author_avatar,
        digg_count=video.digg_count,
        comment_count=video.comment_count,
        share_count=video.share_count,
        collect_count=video.collect_count,
        duration_ms=video.duration_ms,
        width=video.width,
        height=video.height,
        music_title=video.music_title,
        music_author=video.music_author,
        image_count=len(video.image_urls or []),
        cover_url=f"/api/videos/{video.aweme_id}/cover" if video.cover_local_path else None,
        original_url=f"https://www.douyin.com/video/{video.aweme_id}",
        download_status=video.download_status,
        video_local_path=video.video_local_path,
        downloaded_at=video.downloaded_at,
        download_error=video.download_error,
        is_bookmarked=video.is_bookmarked,
        bookmarked_at=video.bookmarked_at,
        bookmark_collection=video.bookmark_collection,
        bookmark_note=video.bookmark_note,
    )
