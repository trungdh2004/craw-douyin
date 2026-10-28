from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.anti_bot import (
    format_edit_studio_base_url,
    get_or_create_anti_bot_settings,
)
from douyin_crawler.models import CrawlTarget, DouyinVideo, VideoSource
from douyin_crawler.settings import get_settings
from douyin_crawler.targets import TargetCreate, TargetService, TargetType

SortField = Literal[
    "create_time",
    "crawled_at",
    "digg_count",
    "share_count",
    "comment_count",
    "collect_count",
    "duration_ms",
    "edit_sent_at",
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
    edit_item_id: str | None = None
    edit_list_id: str | None = None
    edit_sent_at: datetime | None = None
    edit_status: str | None = None
    edit_error: str | None = None
    edit_studio_url: str | None = None


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


class TrendingHashtagItem(BaseModel):
    tag: str
    video_count: int
    total_digg: int


class TrendingMusicItem(BaseModel):
    title: str
    author: str | None
    video_count: int
    total_digg: int


class SuggestedTopicItem(BaseModel):
    keyword: str
    label: str
    category: str


class TrendsResponse(BaseModel):
    trending_hashtags: list[TrendingHashtagItem]
    trending_music: list[TrendingMusicItem]
    suggested_topics: list[SuggestedTopicItem]


SUGGESTED_DOUYIN_TOPICS: list[SuggestedTopicItem] = [
    SuggestedTopicItem(keyword="穿搭", label="Phối đồ OOTD (穿搭)", category="Thời trang"),
    SuggestedTopicItem(keyword="美食", label="Ẩm thực & Nấu ăn (美食)", category="Ẩm thực"),
    SuggestedTopicItem(keyword="好物分享", label="Review Đồ hay (好物分享)", category="Kinh doanh / Affiliate"),
    SuggestedTopicItem(keyword="美妆护肤", label="Làm đẹp & Skincare (美妆护肤)", category="Làm đẹp"),
    SuggestedTopicItem(keyword="生活小妙招", label="Mẹo vặt Đời sống (生活小妙招)", category="Đời sống"),
    SuggestedTopicItem(keyword="数码评测", label="Đồ Công nghệ (数码评测)", category="Công nghệ"),
    SuggestedTopicItem(keyword="搞笑日常", label="Hài hước / Giải trí (搞笑日常)", category="Giải trí"),
    SuggestedTopicItem(keyword="萌宠", label="Thú cưng đáng yêu (萌宠)", category="Thú cưng"),
    SuggestedTopicItem(keyword="旅行风景", label="Du lịch & Cảnh đẹp (旅行风景)", category="Du lịch"),
    SuggestedTopicItem(keyword="AI创作", label="Video AI Xu hướng (AI创作)", category="Công nghệ"),
]


SORT_COLUMNS = {
    "create_time": DouyinVideo.create_time,
    "crawled_at": DouyinVideo.crawled_at,
    "digg_count": DouyinVideo.digg_count,
    "share_count": DouyinVideo.share_count,
    "comment_count": DouyinVideo.comment_count,
    "collect_count": DouyinVideo.collect_count,
    "duration_ms": DouyinVideo.duration_ms,
    "edit_sent_at": func.coalesce(DouyinVideo.edit_sent_at, DouyinVideo.updated_at),
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
        is_analyzed: bool | None = None,
        edit_status: Literal["SENT", "FAILED"] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        crawled_from: datetime | None = None,
        crawled_to: datetime | None = None,
        sort: SortField = "crawled_at",
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
        if is_analyzed is True:
            statement = statement.where(
                or_(
                    DouyinVideo.edit_item_id.is_not(None),
                    DouyinVideo.edit_status.is_not(None),
                )
            )
        elif is_analyzed is False:
            statement = statement.where(
                DouyinVideo.edit_item_id.is_(None),
                DouyinVideo.edit_status.is_(None),
            )
        if edit_status == "SENT":
            statement = statement.where(
                or_(
                    DouyinVideo.edit_status == "SENT",
                    and_(
                        DouyinVideo.edit_status.is_(None),
                        DouyinVideo.edit_item_id.is_not(None),
                    ),
                )
            )
        elif edit_status == "FAILED":
            statement = statement.where(DouyinVideo.edit_status == "FAILED")
        if date_from:
            statement = statement.where(DouyinVideo.create_time >= date_from)
        if date_to:
            statement = statement.where(DouyinVideo.create_time <= date_to)
        if crawled_from:
            statement = statement.where(DouyinVideo.crawled_at >= crawled_from)
        if crawled_to:
            statement = statement.where(DouyinVideo.crawled_at <= crawled_to)
        async with sessions() as session:
            settings = await get_or_create_anti_bot_settings(session)
            edit_base_url = format_edit_studio_base_url(
                settings.edit_studio_host, settings.edit_studio_port
            )
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
            items=[
                _response(video, source_names.get(video.aweme_id, []), edit_base_url)
                for video in videos
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    @router.get("/{aweme_id}/cover", response_model=None)
    async def local_cover(aweme_id: str) -> Response:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Cover not found")
        repo_root = Path(__file__).parents[2]
        candidates: list[Path] = []
        if video.cover_local_path:
            raw_path = Path(video.cover_local_path)
            candidates.append(raw_path)
            if not raw_path.is_absolute():
                candidates.append(repo_root / raw_path)
        candidates.append(get_settings().covers_directory / f"{aweme_id}.jpg")
        candidates.append(repo_root / "covers" / f"{aweme_id}.jpg")
        for candidate in candidates:
            if candidate.is_file():
                return FileResponse(candidate, media_type="image/jpeg")
        if video.cover_url and video.cover_url.startswith("http"):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                    res = await client.get(
                        video.cover_url,
                        headers={"Referer": "https://www.douyin.com/"},
                    )
                    if res.status_code < 400 and res.content:
                        return Response(content=res.content, media_type="image/jpeg")
            except Exception:
                pass
        raise HTTPException(status_code=404, detail="Cover not found")

    @router.get("/{aweme_id}/stream", response_model=None)
    async def stream_video(aweme_id: str) -> Response:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Douyin post not found")
        if video.video_local_path and Path(video.video_local_path).is_file():
            return FileResponse(video.video_local_path, media_type="video/mp4")
        if video.raw_video_url:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                res = await client.get(
                    video.raw_video_url,
                    headers={"Referer": "https://www.douyin.com/"},
                )
                if res.status_code < 400 and res.content:
                    return Response(content=res.content, media_type="video/mp4")
        raise HTTPException(status_code=404, detail="Local video file not found")

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

    @router.delete("/{aweme_id}/edit-status")
    async def clear_edit_status(aweme_id: str) -> VideoResponse:
        async with sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if video is None:
                raise HTTPException(status_code=404, detail="Douyin post not found")
            video.edit_item_id = None
            video.edit_list_id = None
            video.edit_sent_at = None
            video.edit_status = None
            video.edit_error = None
            video.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(video)
            settings = await get_or_create_anti_bot_settings(session)
            edit_base_url = format_edit_studio_base_url(
                settings.edit_studio_host, settings.edit_studio_port
            )
            source_rows = (
                await session.execute(
                    select(CrawlTarget.name)
                    .join(VideoSource, CrawlTarget.id == VideoSource.target_id)
                    .where(VideoSource.aweme_id == aweme_id)
                )
            ).scalars().all()
            return _response(video, list(source_rows), edit_base_url)

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


def create_trends_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(prefix="/api/trends", tags=["trends"])

    @router.get("")
    async def get_trends() -> TrendsResponse:
        async with sessions() as session:
            videos = list(
                await session.scalars(
                    select(DouyinVideo).order_by(DouyinVideo.digg_count.desc()).limit(300)
                )
            )
        tag_stats: dict[str, list[int]] = {}
        music_stats: dict[str, tuple[str | None, int, int]] = {}
        for v in videos:
            for raw_tag in v.hashtags or []:
                tag = str(raw_tag).strip()
                if not tag:
                    continue
                if tag not in tag_stats:
                    tag_stats[tag] = [0, 0]
                tag_stats[tag][0] += 1
                tag_stats[tag][1] += int(v.digg_count or 0)
            if v.music_title:
                title = v.music_title.strip()
                if title:
                    prev_author, cnt, digg = music_stats.get(title, (v.music_author, 0, 0))
                    music_stats[title] = (prev_author, cnt + 1, digg + int(v.digg_count or 0))

        trending_hashtags = [
            TrendingHashtagItem(tag=t, video_count=vals[0], total_digg=vals[1])
            for t, vals in sorted(
                tag_stats.items(), key=lambda x: (x[1][1], x[1][0]), reverse=True
            )[:12]
        ]
        trending_music = [
            TrendingMusicItem(
                title=title, author=vals[0], video_count=vals[1], total_digg=vals[2]
            )
            for title, vals in sorted(
                music_stats.items(), key=lambda x: (x[1][2], x[1][1]), reverse=True
            )[:8]
        ]
        return TrendsResponse(
            trending_hashtags=trending_hashtags,
            trending_music=trending_music,
            suggested_topics=SUGGESTED_DOUYIN_TOPICS,
        )

    return router


def _response(
    video: DouyinVideo,
    source_names: list[str],
    edit_base_url: str | None = None,
) -> VideoResponse:
    if video.aweme_type == 68:
        original_url = f"https://www.douyin.com/note/{video.aweme_id}"
    elif video.author_sec_uid:
        original_url = (
            f"https://www.douyin.com/user/{video.author_sec_uid}?modal_id={video.aweme_id}"
        )
    else:
        original_url = f"https://www.douyin.com/discover?modal_id={video.aweme_id}"
    resolved_base_url = (edit_base_url or get_settings().edit_douyin_url).rstrip("/")
    effective_edit_status = (
        video.edit_status
        if video.edit_status
        else ("SENT" if video.edit_item_id else None)
    )
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
        cover_url=(
            f"/api/videos/{video.aweme_id}/cover"
            if (video.cover_local_path or video.cover_url)
            else None
        ),
        original_url=original_url,
        download_status=video.download_status,
        video_local_path=video.video_local_path,
        downloaded_at=video.downloaded_at,
        download_error=video.download_error,
        is_bookmarked=video.is_bookmarked,
        bookmarked_at=video.bookmarked_at,
        bookmark_collection=video.bookmark_collection,
        bookmark_note=video.bookmark_note,
        edit_item_id=video.edit_item_id,
        edit_list_id=video.edit_list_id,
        edit_sent_at=video.edit_sent_at,
        edit_status=effective_edit_status,
        edit_error=video.edit_error,
        edit_studio_url=(
            f"{resolved_base_url}/items/{video.edit_item_id}"
            if video.edit_item_id
            else None
        ),
    )
