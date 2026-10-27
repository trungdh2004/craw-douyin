from __future__ import annotations

import asyncio
import random
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.anti_bot import PRESET_DEFAULTS, get_or_create_anti_bot_settings
from douyin_crawler.browser import BrowserSessionManager
from douyin_crawler.models import CrawlLog, CrawlTarget, DouyinVideo, VideoSource


class CaptchaDetectedError(RuntimeError):
    """Raised when Douyin presents a Captcha or verification block."""


@dataclass(frozen=True)
class ScrapedPost:
    aweme_id: str
    aweme_type: int
    description: str
    hashtags: list[str]
    create_time: datetime
    author_sec_uid: str
    author_nickname: str
    author_avatar: str | None
    digg_count: int
    comment_count: int
    share_count: int
    collect_count: int
    cover_url: str | None
    video_url: str | None
    image_urls: list[str]
    is_top: bool = False
    duration_ms: int = 0
    width: int | None = None
    height: int | None = None
    music_title: str | None = None
    music_author: str | None = None


class DouyinContentAdapter(Protocol):
    def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]: ...

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost: ...


class MediaHttpAdapter(Protocol):
    async def fetch(self, url: str) -> tuple[int, bytes]: ...


class HttpxMediaAdapter:
    async def fetch(self, url: str) -> tuple[int, bytes]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            response = await client.get(url, headers={"Referer": "https://www.douyin.com/"})
            return response.status_code, response.content


class PlaywrightDouyinContentAdapter:
    _STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = window.chrome || { runtime: {} };
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sessions = sessions

    async def _load_anti_bot(self) -> dict[str, Any]:
        if self._sessions is None:
            return {
                **PRESET_DEFAULTS["BALANCED"],
                "user_agent": None,
                "proxy_url": None,
            }
        async with self._sessions() as session:
            cfg = await get_or_create_anti_bot_settings(session)
            return {
                "scroll_delay_min_ms": cfg.scroll_delay_min_ms,
                "scroll_delay_max_ms": cfg.scroll_delay_max_ms,
                "stealth_mode": cfg.stealth_mode,
                "human_scroll": cfg.human_scroll,
                "auto_stop_on_captcha": cfg.auto_stop_on_captcha,
                "max_pages_per_run": cfg.max_pages_per_run,
                "user_agent": cfg.user_agent,
                "proxy_url": cfg.proxy_url,
            }

    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        from playwright.async_api import async_playwright

        cfg = await self._load_anti_bot()
        queue: asyncio.Queue[list[ScrapedPost]] = asyncio.Queue()
        captcha_triggered = False
        endpoints: tuple[str, ...]
        if target.target_type == "CHANNEL":
            endpoints = ("aweme/post",)
        elif target.target_type == "COLLECT":
            endpoints = ("listcollection", "aweme/favorite")
        else:
            endpoints = ("general/search",)
        launch_kwargs: dict[str, Any] = {"headless": True}
        if cfg.get("user_agent"):
            launch_kwargs["user_agent"] = cfg["user_agent"]
        if cfg.get("proxy_url"):
            launch_kwargs["proxy"] = {"server": cfg["proxy_url"]}
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(profile), **launch_kwargs
            )
            if cfg.get("stealth_mode", True):
                await context.add_init_script(self._STEALTH_SCRIPT)
            page = context.pages[0] if context.pages else await context.new_page()

            async def capture(response: Any) -> None:
                nonlocal captcha_triggered
                if "verify" in response.url and "captcha" in response.url:
                    captcha_triggered = True
                    return
                if not any(ep in response.url for ep in endpoints):
                    return
                try:
                    payload = await response.json()
                    raw_posts = payload.get("aweme_list") or payload.get("data", [])
                    posts = [self._normalize(item) for item in raw_posts if item.get("aweme_id")]
                    if posts:
                        await queue.put(posts)
                except Exception:
                    return

            page.on("response", lambda response: asyncio.create_task(capture(response)))
            url = self._target_url(target)
            try:
                await page.goto(url, wait_until="domcontentloaded")
                yielded = 0
                pages = 0
                max_pages = int(cfg.get("max_pages_per_run", 25))
                while yielded < target.max_items_per_run and pages < max_pages:
                    if captcha_triggered and cfg.get("auto_stop_on_captcha", True):
                        raise CaptchaDetectedError("Douyin yêu cầu giải Captcha xác thực")
                    try:
                        posts = await asyncio.wait_for(queue.get(), timeout=12)
                    except TimeoutError:
                        break
                    yield posts
                    yielded += len(posts)
                    pages += 1
                    if cfg.get("human_scroll", True):
                        for step in (550, 650, 400):
                            await page.mouse.wheel(0, step + random.randint(-80, 120))
                            await page.wait_for_timeout(random.randint(120, 280))
                    else:
                        await page.mouse.wheel(0, 1600)
                    delay_ms = random.randint(
                        int(cfg.get("scroll_delay_min_ms", 1500)),
                        int(cfg.get("scroll_delay_max_ms", 3500)),
                    )
                    await page.wait_for_timeout(delay_ms)
            finally:
                await context.close()

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        from playwright.async_api import async_playwright

        result: asyncio.Future[ScrapedPost] = asyncio.get_running_loop().create_future()
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(str(profile), headless=True)
            page = context.pages[0] if context.pages else await context.new_page()

            async def capture(response: Any) -> None:
                if "aweme/detail" not in response.url or result.done():
                    return
                try:
                    payload = await response.json()
                    item = payload.get("aweme_detail")
                    if item:
                        result.set_result(self._normalize(item))
                except Exception:
                    return

            page.on("response", lambda response: asyncio.create_task(capture(response)))
            target_url = aweme_id if aweme_id.startswith("http") else f"https://www.douyin.com/video/{aweme_id}"
            try:
                await page.goto(target_url, wait_until="domcontentloaded")
                return await asyncio.wait_for(result, timeout=15)
            finally:
                await context.close()

    @staticmethod
    def _target_url(target: CrawlTarget) -> str:
        if target.target_type == "KEYWORD":
            return f"https://www.douyin.com/search/{quote(target.target_value)}"
        if target.target_type == "COLLECT":
            if target.target_value.startswith("http"):
                return target.target_value
            return "https://www.douyin.com/user/self?showTab=favorite_collection"
        if target.target_value.startswith("http"):
            return target.target_value
        return f"https://www.douyin.com/user/{target.target_value}"

    @staticmethod
    def _normalize(item: dict[str, Any]) -> ScrapedPost:
        author = item.get("author") or {}
        statistics = item.get("statistics") or {}
        video = item.get("video") or {}
        music = item.get("music") or {}
        cover = video.get("cover") or {}
        play = video.get("play_addr") or {}
        images = item.get("images") or []
        raw_duration = video.get("duration") or item.get("duration") or 0
        width = video.get("width")
        height = video.get("height")
        return ScrapedPost(
            aweme_id=str(item["aweme_id"]),
            aweme_type=int(item.get("aweme_type", 0)),
            description=item.get("desc") or "",
            hashtags=[entry.get("hashtag_name", "") for entry in item.get("text_extra", []) if entry.get("hashtag_name")],
            create_time=datetime.fromtimestamp(int(item.get("create_time", 0)), UTC),
            author_sec_uid=author.get("sec_uid") or "",
            author_nickname=author.get("nickname") or "",
            author_avatar=((author.get("avatar_thumb") or {}).get("url_list") or [None])[0],
            digg_count=int(statistics.get("digg_count", 0)),
            comment_count=int(statistics.get("comment_count", 0)),
            share_count=int(statistics.get("share_count", 0)),
            collect_count=int(statistics.get("collect_count", 0)),
            cover_url=(cover.get("url_list") or [None])[0],
            video_url=(play.get("url_list") or [None])[0],
            image_urls=[(image.get("url_list") or [""])[0] for image in images],
            is_top=bool(item.get("is_top", 0)),
            duration_ms=int(raw_duration),
            width=int(width) if width is not None else None,
            height=int(height) if height is not None else None,
            music_title=music.get("title"),
            music_author=music.get("author"),
        )


def parse_douyin_identifier(raw: str) -> str:
    text = raw.strip()
    video_match = re.search(r"douyin\.com/(?:video|note)/(\d{10,25})", text)
    if video_match:
        return video_match.group(1)
    modal_match = re.search(r"modal_id=(\d{10,25})", text)
    if modal_match:
        return modal_match.group(1)
    if re.fullmatch(r"\d{10,25}", text):
        return text
    url_match = re.search(r"https?://[^\s\"'<>]+", text)
    if url_match:
        return url_match.group(0).rstrip(".,;)")
    id_match = re.search(r"\b(\d{15,22})\b", text)
    if id_match:
        return id_match.group(1)
    return text


class SingleCrawlRequest(BaseModel):
    inputs: list[str] = Field(min_length=1, max_length=100)
    auto_download: bool = False
    is_bookmarked: bool = False
    bookmark_collection: str | None = None
    run_at: datetime | None = None


class CrawlRunner:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        browser: BrowserSessionManager,
        content: DouyinContentAdapter,
        media: MediaHttpAdapter,
        covers_directory: Path,
        download_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._sessions = sessions
        self._browser = browser
        self._content = content
        self._media = media
        self._covers_directory = covers_directory
        self._download_callback = download_callback
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, target_id: int, trigger_type: str = "MANUAL") -> None:
        task = asyncio.create_task(self.run(target_id, trigger_type=trigger_type))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def start_items(
        self,
        log_id: int,
        inputs: list[str],
        *,
        auto_download: bool = False,
        is_bookmarked: bool = False,
        bookmark_collection: str | None = None,
    ) -> None:
        task = asyncio.create_task(
            self.run_items(
                log_id,
                inputs,
                auto_download=auto_download,
                is_bookmarked=is_bookmarked,
                bookmark_collection=bookmark_collection,
            )
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait(self) -> None:
        while self._tasks:
            pending = list(self._tasks)
            await asyncio.gather(*pending)

    async def run(self, target_id: int, trigger_type: str = "MANUAL") -> None:
        new_ids: list[str] = []
        auto_download = False
        async with self._sessions() as session:
            target = await session.get(CrawlTarget, target_id)
            if target is None:
                return
            auto_download = target.auto_download
            log = CrawlLog(
                target_id=target_id,
                job_type="TARGET_CRAWL",
                trigger_type=trigger_type,
                input_summary=f"{target.target_type}: {target.name}",
                payload={"target_id": target_id},
                status="RUNNING",
            )
            target.last_status = "RUNNING"
            session.add(log)
            await session.commit()
            try:
                counts, new_ids = await self._browser.run_with_profile(
                    lambda profile: self._crawl(session, target, profile)
                )
                log.new_videos_count, log.updated_videos_count = counts
                log.status = target.last_status = "SUCCESS"
            except CaptchaDetectedError as error:
                log.status = "CAPTCHA_BLOCKED"
                target.last_status = "FAILED"
                log.error_message = str(error)
                self._browser.mark_captcha_required()
            except Exception as error:
                log.status = target.last_status = "FAILED"
                log.error_message = str(error)
            log.finished_at = target.last_run_at = datetime.now(UTC)
            if target.schedule_type == "ONCE":
                target.is_active = False
            await session.commit()
        if auto_download and self._download_callback is not None:
            for aweme_id in new_ids:
                await self._download_callback(aweme_id)

    async def run_items(
        self,
        log_id: int,
        inputs: list[str],
        *,
        auto_download: bool = False,
        is_bookmarked: bool = False,
        bookmark_collection: str | None = None,
    ) -> None:
        crawled_ids: list[str] = []
        async with self._sessions() as session:
            log = await session.get(CrawlLog, log_id)
            if log is None:
                return
            log.status = "RUNNING"
            log.started_at = datetime.now(UTC)
            await session.commit()
            try:
                new_count, updated_count, crawled_ids = await self._browser.run_with_profile(
                    lambda profile: self._crawl_items(
                        session,
                        profile,
                        inputs,
                        is_bookmarked=is_bookmarked,
                        bookmark_collection=bookmark_collection,
                    )
                )
                log.new_videos_count = new_count
                log.updated_videos_count = updated_count
                log.status = "SUCCESS"
            except CaptchaDetectedError as error:
                log.status = "CAPTCHA_BLOCKED"
                log.error_message = str(error)
                self._browser.mark_captcha_required()
            except Exception as error:
                log.status = "FAILED"
                log.error_message = str(error)
            log.finished_at = datetime.now(UTC)
            await session.commit()
        if auto_download and self._download_callback is not None:
            for aweme_id in crawled_ids:
                await self._download_callback(aweme_id)

    async def _crawl_items(
        self,
        session: AsyncSession,
        profile: Path,
        inputs: list[str],
        *,
        is_bookmarked: bool,
        bookmark_collection: str | None,
    ) -> tuple[int, int, list[str]]:
        new_count = updated_count = 0
        crawled_ids: list[str] = []
        for raw in inputs:
            token = parse_douyin_identifier(raw)
            if not token:
                continue
            post = await self._content.detail(profile, token)
            existing = await session.get(DouyinVideo, post.aweme_id)
            if existing is not None:
                self._update_metrics(existing, post)
                if is_bookmarked:
                    existing.is_bookmarked = True
                    if existing.bookmarked_at is None:
                        existing.bookmarked_at = datetime.now(UTC)
                    if bookmark_collection:
                        existing.bookmark_collection = bookmark_collection
                updated_count += 1
            else:
                cover_path = await self._save_cover(post)
                video = self._video(None, post, cover_path)
                if is_bookmarked:
                    video.is_bookmarked = True
                    video.bookmarked_at = datetime.now(UTC)
                    video.bookmark_collection = bookmark_collection
                session.add(video)
                new_count += 1
            crawled_ids.append(post.aweme_id)
            await session.flush()
        return new_count, updated_count, crawled_ids

    async def _crawl(
        self, session: AsyncSession, target: CrawlTarget, profile: Path
    ) -> tuple[tuple[int, int], list[str]]:
        new_count = updated_count = scanned = consecutive_existing = 0
        new_ids: list[str] = []
        stop = False
        async for page in self._content.crawl(profile, target):
            for post in page:
                if scanned >= target.max_items_per_run:
                    stop = True
                    break
                scanned += 1
                existing = await session.get(DouyinVideo, post.aweme_id)
                if existing is not None:
                    source = await session.get(VideoSource, (post.aweme_id, target.id))
                    if source is None:
                        session.add(VideoSource(aweme_id=post.aweme_id, target_id=target.id))
                    self._update_metrics(existing, post)
                    if target.target_type == "COLLECT":
                        existing.is_bookmarked = True
                        if existing.bookmarked_at is None:
                            existing.bookmarked_at = datetime.now(UTC)
                        if not existing.bookmark_collection:
                            existing.bookmark_collection = target.name
                    updated_count += 1
                    if target.target_type == "CHANNEL" and not post.is_top:
                        consecutive_existing += 1
                        if consecutive_existing >= 3:
                            stop = True
                            break
                    continue
                consecutive_existing = 0
                cover_path = await self._save_cover(post)
                video = self._video(target.id, post, cover_path)
                if target.target_type == "COLLECT":
                    video.is_bookmarked = True
                    video.bookmarked_at = datetime.now(UTC)
                    video.bookmark_collection = target.name
                session.add(video)
                await session.flush()
                session.add(VideoSource(aweme_id=post.aweme_id, target_id=target.id))
                new_count += 1
                new_ids.append(post.aweme_id)
            await session.flush()
            if stop:
                break
        return (new_count, updated_count), new_ids

    async def _save_cover(self, post: ScrapedPost) -> str | None:
        if not post.cover_url:
            return None
        status, content = await self._media.fetch(post.cover_url)
        if status >= 400:
            raise RuntimeError(f"Cover download returned HTTP {status}")
        self._covers_directory.mkdir(parents=True, exist_ok=True)
        path = self._covers_directory / f"{post.aweme_id}.jpg"
        path.write_bytes(content)
        return str(path)

    @staticmethod
    def _update_metrics(video: DouyinVideo, post: ScrapedPost) -> None:
        video.digg_count = post.digg_count
        video.comment_count = post.comment_count
        video.share_count = post.share_count
        video.collect_count = post.collect_count
        if post.duration_ms:
            video.duration_ms = post.duration_ms
        if post.width is not None:
            video.width = post.width
        if post.height is not None:
            video.height = post.height
        if post.music_title is not None:
            video.music_title = post.music_title
        if post.music_author is not None:
            video.music_author = post.music_author
        video.updated_at = datetime.now(UTC)

    @staticmethod
    def _video(target_id: int | None, post: ScrapedPost, cover_path: str | None) -> DouyinVideo:
        return DouyinVideo(
            aweme_id=post.aweme_id, target_id=target_id, aweme_type=post.aweme_type,
            description=post.description, hashtags=post.hashtags, create_time=post.create_time,
            author_sec_uid=post.author_sec_uid, author_nickname=post.author_nickname,
            author_avatar=post.author_avatar, digg_count=post.digg_count,
            comment_count=post.comment_count, share_count=post.share_count,
            collect_count=post.collect_count, duration_ms=post.duration_ms,
            width=post.width, height=post.height,
            music_title=post.music_title, music_author=post.music_author,
            cover_remote_url=post.cover_url,
            cover_local_path=cover_path, raw_video_url=post.video_url, image_urls=post.image_urls,
        )


def create_crawl_router(
    sessions: async_sessionmaker[AsyncSession],
    crawl_runner: CrawlRunner,
    scheduler: AsyncIOScheduler,
) -> APIRouter:
    router = APIRouter(prefix="/api/crawl", tags=["crawl"])

    @router.post("/items", status_code=202)
    async def crawl_items(payload: SingleCrawlRequest) -> dict[str, object]:
        cleaned = [line.strip() for line in payload.inputs if line.strip()]
        summary = ", ".join(parse_douyin_identifier(item) for item in cleaned[:3])
        if len(cleaned) > 3:
            summary += f" (+{len(cleaned) - 3})"
        now = datetime.now(UTC)
        is_scheduled = payload.run_at is not None and payload.run_at > now
        async with sessions() as session:
            log = CrawlLog(
                target_id=None,
                job_type="SINGLE_CRAWL",
                trigger_type="ONCE" if is_scheduled else "MANUAL",
                input_summary=summary,
                payload={
                    "inputs": cleaned,
                    "auto_download": payload.auto_download,
                    "is_bookmarked": payload.is_bookmarked,
                    "bookmark_collection": payload.bookmark_collection,
                    "run_at": payload.run_at.isoformat() if payload.run_at else None,
                },
                status="SCHEDULED" if is_scheduled else "RUNNING",
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            log_id = log.id

        if is_scheduled and payload.run_at is not None:
            scheduler.add_job(
                crawl_runner.start_items,
                DateTrigger(run_date=payload.run_at),
                args=[log_id, cleaned],
                kwargs={
                    "auto_download": payload.auto_download,
                    "is_bookmarked": payload.is_bookmarked,
                    "bookmark_collection": payload.bookmark_collection,
                },
                id=f"single-crawl-{log_id}",
                replace_existing=True,
            )
            return {"status": "SCHEDULED", "log_id": log_id, "count": len(cleaned)}

        crawl_runner.start_items(
            log_id,
            cleaned,
            auto_download=payload.auto_download,
            is_bookmarked=payload.is_bookmarked,
            bookmark_collection=payload.bookmark_collection,
        )
        return {"status": "RUNNING", "log_id": log_id, "count": len(cleaned)}

    return router
