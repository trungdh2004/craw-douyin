import asyncio
import re
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.browser import BrowserSessionManager
from douyin_crawler.crawler import DouyinContentAdapter, MediaHttpAdapter
from douyin_crawler.models import CrawlLog, DouyinVideo


class BatchDownloadRequest(BaseModel):
    aweme_ids: list[str] = Field(min_length=1, max_length=100)


class AwemeType(IntEnum):
    IMAGE_ALBUM = 68


class DownloadRunner:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], browser: BrowserSessionManager,
                 content: DouyinContentAdapter, media: MediaHttpAdapter, downloads_directory: Path) -> None:
        self._sessions = sessions
        self._browser = browser
        self._content = content
        self._media = media
        self._directory = downloads_directory
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(
        self,
        aweme_id: str,
        *,
        trigger_type: str = "MANUAL",
        record_log: bool = False,
    ) -> None:
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if video is None:
                raise HTTPException(status_code=404, detail="Douyin post not found")
            if video.download_status == "DOWNLOADING":
                return
            video.download_status = "DOWNLOADING"
            video.download_error = None
            await session.commit()
        task = asyncio.create_task(
            self._download(aweme_id, trigger_type=trigger_type, record_log=record_log)
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def ensure_downloaded(self, aweme_id: str) -> Path:
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if video is None:
                raise HTTPException(status_code=404, detail="Không tìm thấy video")
            if video.aweme_type == AwemeType.IMAGE_ALBUM:
                raise HTTPException(
                    status_code=422,
                    detail=f"Bài đăng {aweme_id} là Album ảnh, không phải video MP4",
                )
            if (
                video.download_status == "COMPLETED"
                and video.video_local_path
                and Path(video.video_local_path).is_file()
            ):
                return Path(video.video_local_path).resolve()
            video.download_status = "DOWNLOADING"
            video.download_error = None
            await session.commit()

        await self._download(aweme_id, trigger_type="MANUAL", record_log=False)

        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if (
                video is None
                or video.download_status != "COMPLETED"
                or not video.video_local_path
                or not Path(video.video_local_path).is_file()
            ):
                err = (video.download_error if video else None) or "Không thể tải file MP4"
                raise HTTPException(status_code=502, detail=err)
            return Path(video.video_local_path).resolve()

    async def wait(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks)

    async def _download(
        self,
        aweme_id: str,
        *,
        trigger_type: str = "MANUAL",
        record_log: bool = False,
    ) -> None:
        started_at = datetime.now(UTC)
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            assert video is not None
            try:
                if self._expired(video.raw_video_url):
                    await self._refresh(video)
                date_folder = self._date_folder(video)
                if video.aweme_type == AwemeType.IMAGE_ALBUM:
                    folder = date_folder / video.aweme_id
                    folder.mkdir(parents=True, exist_ok=True)
                    for index, url in enumerate(list(video.image_urls), start=1):
                        status, content = await self._media.fetch(url)
                        if status == 403:
                            await self._refresh(video)
                            refreshed_url = video.image_urls[index - 1]
                            status, content = await self._media.fetch(refreshed_url)
                        if status >= 400:
                            raise RuntimeError(f"Image download returned HTTP {status}")
                        (folder / f"{index:02}.jpg").write_bytes(content)
                    local_path = folder
                else:
                    date_folder.mkdir(parents=True, exist_ok=True)
                    status, content = await self._media.fetch(video.raw_video_url or "")
                    if status == 403:
                        await self._refresh(video)
                        status, content = await self._media.fetch(video.raw_video_url or "")
                    if status >= 400:
                        raise RuntimeError(f"Video download returned HTTP {status}")
                    local_path = date_folder / f"{video.aweme_id}.mp4"
                    local_path.write_bytes(content)
                video.video_local_path = str(local_path)
                video.download_status = "COMPLETED"
                video.downloaded_at = datetime.now(UTC)
                if record_log or trigger_type == "RETRY":
                    session.add(
                        CrawlLog(
                            target_id=video.target_id,
                            job_type="DOWNLOAD",
                            trigger_type=trigger_type,
                            input_summary=f"Tải media: {aweme_id}",
                            payload={"aweme_id": aweme_id},
                            started_at=started_at,
                            finished_at=datetime.now(UTC),
                            status="SUCCESS",
                            new_videos_count=0,
                            updated_videos_count=1,
                        )
                    )
            except Exception as error:
                err_msg = str(error).strip() or repr(error)
                video.download_status = "FAILED"
                video.download_error = err_msg
                session.add(
                    CrawlLog(
                        target_id=video.target_id,
                        job_type="DOWNLOAD",
                        trigger_type=trigger_type,
                        input_summary=f"Tải media: {aweme_id}",
                        payload={"aweme_id": aweme_id},
                        started_at=started_at,
                        finished_at=datetime.now(UTC),
                        status="FAILED",
                        error_message=err_msg,
                    )
                )
            await session.commit()

    async def _refresh(self, video: DouyinVideo) -> None:
        post = await self._browser.run_with_profile(
            lambda profile: self._content.detail(profile, video.aweme_id)
        )
        video.raw_video_url = post.video_url
        video.image_urls = post.image_urls

    def _date_folder(self, video: DouyinVideo) -> Path:
        channel = re.sub(r"[^\w.-]+", "_", video.author_nickname, flags=re.UNICODE).strip("_") or video.author_sec_uid
        return self._directory / channel / video.create_time.date().isoformat()

    @staticmethod
    def _expired(url: str | None) -> bool:
        if not url:
            return True
        now_ts = int(datetime.now(UTC).timestamp())
        values = parse_qs(urlparse(url).query).get("x-expires")
        if values and int(values[0]) <= now_ts:
            return True
        path_match = re.search(r"/[0-9a-f]{32}/([0-9a-f]{8})/", urlparse(url).path)
        if path_match and int(path_match.group(1), 16) <= now_ts:
            return True
        return False


def create_downloads_router(runner: DownloadRunner) -> APIRouter:
    router = APIRouter(prefix="/api/videos", tags=["downloads"])

    @router.post("/{aweme_id}/download", status_code=202)
    async def download(aweme_id: str) -> dict[str, str]:
        await runner.start(aweme_id)
        return {"status": "DOWNLOADING"}

    @router.post("/batch-download", status_code=202)
    async def batch_download(payload: BatchDownloadRequest) -> dict[str, object]:
        for aweme_id in dict.fromkeys(payload.aweme_ids):
            await runner.start(aweme_id)
        return {"status": "DOWNLOADING", "accepted": len(set(payload.aweme_ids))}

    return router
