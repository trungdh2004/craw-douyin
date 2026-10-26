import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.browser import BrowserSessionManager
from douyin_crawler.crawler import DouyinContentAdapter, MediaHttpAdapter
from douyin_crawler.models import DouyinVideo


class BatchDownloadRequest(BaseModel):
    aweme_ids: list[str] = Field(min_length=1, max_length=100)


class DownloadRunner:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], browser: BrowserSessionManager,
                 content: DouyinContentAdapter, media: MediaHttpAdapter, downloads_directory: Path) -> None:
        self._sessions = sessions
        self._browser = browser
        self._content = content
        self._media = media
        self._directory = downloads_directory
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self, aweme_id: str) -> None:
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            if video is None:
                raise HTTPException(status_code=404, detail="Douyin post not found")
            if video.download_status == "DOWNLOADING":
                return
            video.download_status = "DOWNLOADING"
            video.download_error = None
            await session.commit()
        task = asyncio.create_task(self._download(aweme_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks)

    async def _download(self, aweme_id: str) -> None:
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            assert video is not None
            try:
                if self._expired(video.raw_video_url):
                    await self._refresh(video)
                folder = self._folder(video)
                folder.mkdir(parents=True, exist_ok=True)
                if video.aweme_type == 68:
                    for index, url in enumerate(video.image_urls, start=1):
                        status, content = await self._media.fetch(url)
                        if status >= 400:
                            raise RuntimeError(f"Image download returned HTTP {status}")
                        (folder / f"{index:02}.jpg").write_bytes(content)
                    local_path = folder
                else:
                    status, content = await self._media.fetch(video.raw_video_url or "")
                    if status == 403:
                        await self._refresh(video)
                        status, content = await self._media.fetch(video.raw_video_url or "")
                    if status >= 400:
                        raise RuntimeError(f"Video download returned HTTP {status}")
                    local_path = folder / f"{video.aweme_id}.mp4"
                    local_path.write_bytes(content)
                video.video_local_path = str(local_path)
                video.download_status = "COMPLETED"
                video.downloaded_at = datetime.now(UTC)
            except Exception as error:
                video.download_status = "FAILED"
                video.download_error = str(error)
            await session.commit()

    async def _refresh(self, video: DouyinVideo) -> None:
        post = await self._browser.run_with_profile(
            lambda profile: self._content.detail(profile, video.aweme_id)
        )
        video.raw_video_url = post.video_url
        video.image_urls = post.image_urls

    def _folder(self, video: DouyinVideo) -> Path:
        channel = re.sub(r"[^\w.-]+", "_", video.author_nickname, flags=re.UNICODE).strip("_") or video.author_sec_uid
        return self._directory / channel / video.create_time.date().isoformat() / video.aweme_id

    @staticmethod
    def _expired(url: str | None) -> bool:
        if not url:
            return True
        values = parse_qs(urlparse(url).query).get("x-expires")
        return bool(values and int(values[0]) <= int(datetime.now(UTC).timestamp()))


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
