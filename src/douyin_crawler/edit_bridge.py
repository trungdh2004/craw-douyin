import asyncio
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.anti_bot import (
    format_edit_studio_base_url,
    get_or_create_anti_bot_settings,
)
from douyin_crawler.browser import BrowserSessionManager
from douyin_crawler.crawler import (
    DouyinContentAdapter,
    _print_terminal_log,
    parse_douyin_identifier,
)
from douyin_crawler.downloads import DownloadRunner
from douyin_crawler.models import DouyinVideo


class SendToEditRequest(BaseModel):
    aweme_ids: list[str] = Field(min_length=1, max_length=50)
    auto_process: bool = True
    profile: Literal["detailed", "fast"] = "detailed"


class SendToEditResponse(BaseModel):
    list_id: str
    item_ids: list[str]
    studio_url: str
    edit_base_url: str


class ResolveMp4Request(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class ResolveMp4Response(BaseModel):
    aweme_id: str
    video_local_path: str
    display_name: str


class EditStudioBridge:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        browser: BrowserSessionManager,
        content: DouyinContentAdapter,
        download_runner: DownloadRunner,
        *,
        edit_douyin_url: str = "http://127.0.0.1:8000",
        edit_douyin_directory: Path = Path("/home/trungdh/dev/tools/edit-douyin"),
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._sessions = sessions
        self._browser = browser
        self._content = content
        self._download_runner = download_runner
        self._edit_url = edit_douyin_url.rstrip("/")
        self._edit_dir = edit_douyin_directory
        self._http_client = http_client
        self._start_lock = asyncio.Lock()

    @property
    def edit_base_url(self) -> str:
        return self._edit_url

    async def _resolve_target_edit_url(self) -> str:
        try:
            async with self._sessions() as session:
                settings = await get_or_create_anti_bot_settings(session)
                host = settings.edit_studio_host or "127.0.0.1"
                port = settings.edit_studio_port or 8000
                configured = format_edit_studio_base_url(host, port)
                if configured != "http://127.0.0.1:8000":
                    return configured
        except Exception:
            pass
        return self._edit_url

    async def _is_edit_alive(self, base_url: str | None = None) -> bool:
        target_url = (base_url or self._edit_url).rstrip("/")
        try:
            if self._http_client is not None:
                res = await self._http_client.get(
                    f"{target_url}/api/lists", params={"page": 1, "page_size": 1}
                )
                return res.status_code == 200
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(
                    f"{target_url}/api/lists", params={"page": 1, "page_size": 1}
                )
                return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _is_local_url(url: str) -> bool:
        lower = url.lower()
        return (
            "://127.0.0.1" in lower
            or "://localhost" in lower
            or "://0.0.0.0" in lower
        )

    async def ensure_edit_service_running(self, base_url: str | None = None) -> str:
        target_url = (base_url or await self._resolve_target_edit_url()).rstrip("/")
        if await self._is_edit_alive(target_url):
            return target_url

        if not self._is_local_url(target_url):
            raise HTTPException(
                status_code=503,
                detail=f"Không thể kết nối tới Server Phân tích tại {target_url}",
            )

        async with self._start_lock:
            if await self._is_edit_alive(target_url):
                return target_url

            run_script = self._edit_dir / "scripts" / "run.sh"
            if not run_script.is_file():
                raise HTTPException(
                    status_code=503,
                    detail=f"Dịch vụ edit-douyin tại {target_url} chưa bật và không tìm thấy {run_script}",
                )

            _print_terminal_log(
                0,
                "EditStudio",
                "INFO",
                "START",
                f"Đang tự động khởi động dịch vụ edit-douyin ({run_script}) tại {target_url}...",
            )
            subprocess.Popen(
                ["bash", str(run_script)],
                cwd=str(self._edit_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            for _ in range(30):
                await asyncio.sleep(0.5)
                if await self._is_edit_alive(target_url):
                    _print_terminal_log(
                        0,
                        "EditStudio",
                        "SUCCESS",
                        "DONE",
                        f"Dịch vụ edit-douyin đã sẵn sàng tại {target_url}!",
                    )
                    return target_url

            raise HTTPException(
                status_code=503,
                detail=f"Không thể kết nối tới dịch vụ edit-douyin tại {target_url} sau khi khởi động",
            )

    @staticmethod
    def _format_display_name(video: DouyinVideo) -> str:
        clean_desc = (video.description or video.aweme_id).replace("\n", " ").replace("\r", " ").strip()
        if len(clean_desc) > 55:
            clean_desc = clean_desc[:55].rstrip() + "..."
        raw_name = f"@{video.author_nickname} - {clean_desc} ({video.aweme_id}).mp4"
        return raw_name.replace("/", "_").replace("\\", "_")[:240]

    async def send_videos_to_edit(
        self,
        aweme_ids: list[str],
        *,
        auto_process: bool = True,
        profile: Literal["detailed", "fast"] = "detailed",
    ) -> SendToEditResponse:
        unique_ids = list(dict.fromkeys(aweme_ids))
        target_url = await self._resolve_target_edit_url()
        try:
            target_url = await self.ensure_edit_service_running(target_url)
        except HTTPException as exc:
            await self._record_send_failure(unique_ids, str(exc.detail))
            raise

        import_items: list[dict[str, Any]] = []
        valid_aweme_ids: list[str] = []

        for aweme_id in unique_ids:
            _print_terminal_log(
                0,
                "EditStudio",
                "INFO",
                "DETAIL",
                f"Chuẩn bị file MP4 không logo cho video ID {aweme_id}...",
            )
            local_path = await self._download_runner.ensure_downloaded(aweme_id)
            async with self._sessions() as session:
                video = await session.get(DouyinVideo, aweme_id)
                if video is None:
                    continue
                display_name = self._format_display_name(video)
                source_url = f"https://www.douyin.com/jingxuan?modal_id={video.aweme_id}"
                import_items.append(
                    {
                        "local_video_path": str(local_path),
                        "display_name": display_name,
                        "source_url": source_url,
                    }
                )
                valid_aweme_ids.append(aweme_id)

        if not import_items:
            raise HTTPException(status_code=422, detail="Không có video MP4 hợp lệ để gửi sang Studio")

        payload = {
            "items": import_items,
            "auto_process": auto_process,
            "profile": profile,
        }

        try:
            if self._http_client is not None:
                res = await self._http_client.post(
                    f"{target_url}/api/lists/import-crawler", json=payload
                )
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(
                        f"{target_url}/api/lists/import-crawler", json=payload
                    )
        except Exception as exc:
            err_msg = f"Không thể kết nối tới {target_url}: {exc}"
            await self._record_send_failure(valid_aweme_ids, err_msg)
            raise HTTPException(status_code=502, detail=err_msg) from exc

        if res.status_code >= 400:
            err_msg = f"Lỗi từ edit-douyin ({res.status_code}): {res.text}"
            await self._record_send_failure(valid_aweme_ids, err_msg)
            raise HTTPException(
                status_code=502,
                detail=err_msg,
            )

        data = res.json()
        list_id = str(data["id"])
        created_items = data.get("items") or []
        item_ids = [str(item["id"]) for item in created_items if isinstance(item, dict) and "id" in item]

        now = datetime.now(UTC)
        async with self._sessions() as session:
            for idx, aweme_id in enumerate(valid_aweme_ids):
                video = await session.get(DouyinVideo, aweme_id)
                if video is not None and idx < len(item_ids):
                    video.edit_item_id = item_ids[idx]
                    video.edit_list_id = list_id
                    video.edit_sent_at = now
                    video.edit_status = "SENT"
                    video.edit_error = None
                    video.updated_at = now
            await session.commit()

        studio_url = (
            f"{target_url}/items/{item_ids[0]}"
            if len(item_ids) == 1
            else f"{target_url}/lists/{list_id}"
        )
        _print_terminal_log(
            0,
            "EditStudio",
            "SUCCESS",
            "DONE",
            f"Đã đẩy {len(item_ids)} video sang Edit Studio ({studio_url}) - Tự động phân tích={auto_process}",
        )
        return SendToEditResponse(
            list_id=list_id,
            item_ids=item_ids,
            studio_url=studio_url,
            edit_base_url=target_url,
        )

    async def _record_send_failure(self, aweme_ids: list[str], error_message: str) -> None:
        if not aweme_ids:
            return
        now = datetime.now(UTC)
        async with self._sessions() as session:
            for aweme_id in aweme_ids:
                video = await session.get(DouyinVideo, aweme_id)
                if video is not None:
                    video.edit_sent_at = now
                    video.edit_status = "FAILED"
                    video.edit_error = error_message[:1000]
                    video.updated_at = now
            await session.commit()

    async def resolve_mp4_for_url(self, raw_url: str) -> ResolveMp4Response:
        token = parse_douyin_identifier(raw_url)
        if not token:
            raise HTTPException(status_code=422, detail="URL Douyin không hợp lệ")

        aweme_id: str | None = token if token.isdigit() else None
        async with self._sessions() as session:
            existing = await session.get(DouyinVideo, aweme_id) if aweme_id else None

        if existing is None:
            post = await self._browser.run_with_profile(
                lambda profile: self._content.detail(profile, token)
            )
            aweme_id = post.aweme_id
            async with self._sessions() as session:
                video = await session.get(DouyinVideo, aweme_id)
                if video is None:
                    video = DouyinVideo(
                        aweme_id=post.aweme_id,
                        target_id=None,
                        aweme_type=post.aweme_type,
                        description=post.description,
                        hashtags=post.hashtags,
                        create_time=post.create_time,
                        author_sec_uid=post.author_sec_uid,
                        author_nickname=post.author_nickname,
                        author_avatar=post.author_avatar,
                        digg_count=post.digg_count,
                        comment_count=post.comment_count,
                        share_count=post.share_count,
                        collect_count=post.collect_count,
                        duration_ms=post.duration_ms,
                        width=post.width,
                        height=post.height,
                        music_title=post.music_title,
                        music_author=post.music_author,
                        cover_remote_url=post.cover_url,
                        raw_video_url=post.video_url,
                        image_urls=post.image_urls,
                    )
                    session.add(video)
                    await session.commit()

        assert aweme_id is not None
        local_path = await self._download_runner.ensure_downloaded(aweme_id)
        async with self._sessions() as session:
            video = await session.get(DouyinVideo, aweme_id)
            display_name = self._format_display_name(video) if video else f"{aweme_id}.mp4"

        return ResolveMp4Response(
            aweme_id=aweme_id,
            video_local_path=str(local_path),
            display_name=display_name,
        )


def create_edit_bridge_router(bridge: EditStudioBridge) -> APIRouter:
    router = APIRouter(prefix="/api/videos", tags=["edit-bridge"])

    @router.post("/send-to-edit")
    async def send_to_edit(payload: SendToEditRequest) -> SendToEditResponse:
        return await bridge.send_videos_to_edit(
            payload.aweme_ids,
            auto_process=payload.auto_process,
            profile=payload.profile,
        )

    @router.post("/resolve-mp4")
    async def resolve_mp4(payload: ResolveMp4Request) -> ResolveMp4Response:
        return await bridge.resolve_mp4_for_url(payload.url)

    return router
