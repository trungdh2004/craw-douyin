from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.browser import BrowserSessionManager
from douyin_crawler.models import CrawlLog, CrawlTarget, DouyinVideo


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
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        from playwright.async_api import async_playwright

        queue: asyncio.Queue[list[ScrapedPost]] = asyncio.Queue()
        endpoint = "aweme/post" if target.target_type == "CHANNEL" else "general/search"
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(str(profile), headless=True)
            page = context.pages[0] if context.pages else await context.new_page()

            async def capture(response: Any) -> None:
                if endpoint not in response.url:
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
                while yielded < target.max_items_per_run:
                    try:
                        posts = await asyncio.wait_for(queue.get(), timeout=12)
                    except TimeoutError:
                        break
                    yield posts
                    yielded += len(posts)
                    await page.mouse.wheel(0, 1600)
                    await page.wait_for_timeout(800)
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
            try:
                await page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="domcontentloaded")
                return await asyncio.wait_for(result, timeout=15)
            finally:
                await context.close()

    @staticmethod
    def _target_url(target: CrawlTarget) -> str:
        if target.target_type == "KEYWORD":
            return f"https://www.douyin.com/search/{quote(target.target_value)}"
        if target.target_value.startswith("http"):
            return target.target_value
        return f"https://www.douyin.com/user/{target.target_value}"

    @staticmethod
    def _normalize(item: dict[str, Any]) -> ScrapedPost:
        author = item.get("author") or {}
        statistics = item.get("statistics") or {}
        video = item.get("video") or {}
        cover = video.get("cover") or {}
        play = video.get("play_addr") or {}
        images = item.get("images") or []
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
        )


class CrawlRunner:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        browser: BrowserSessionManager,
        content: DouyinContentAdapter,
        media: MediaHttpAdapter,
        covers_directory: Path,
    ) -> None:
        self._sessions = sessions
        self._browser = browser
        self._content = content
        self._media = media
        self._covers_directory = covers_directory
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, target_id: int) -> None:
        task = asyncio.create_task(self.run(target_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks)

    async def run(self, target_id: int) -> None:
        async with self._sessions() as session:
            target = await session.get(CrawlTarget, target_id)
            if target is None:
                return
            log = CrawlLog(target_id=target_id, status="RUNNING")
            target.last_status = "RUNNING"
            session.add(log)
            await session.commit()
            try:
                counts = await self._browser.run_with_profile(
                    lambda profile: self._crawl(session, target, profile)
                )
                log.new_videos_count, log.updated_videos_count = counts
                log.status = target.last_status = "SUCCESS"
            except Exception as error:
                log.status = target.last_status = "FAILED"
                log.error_message = str(error)
            log.finished_at = target.last_run_at = datetime.now(UTC)
            await session.commit()

    async def _crawl(self, session: AsyncSession, target: CrawlTarget, profile: Path) -> tuple[int, int]:
        new_count = updated_count = scanned = consecutive_existing = 0
        stop = False
        async for page in self._content.crawl(profile, target):
            for post in page:
                if scanned >= target.max_items_per_run:
                    stop = True
                    break
                scanned += 1
                existing = await session.get(DouyinVideo, post.aweme_id)
                if existing is not None:
                    self._update_metrics(existing, post)
                    updated_count += 1
                    if target.target_type == "CHANNEL" and not post.is_top:
                        consecutive_existing += 1
                        if consecutive_existing >= 3:
                            stop = True
                            break
                    continue
                consecutive_existing = 0
                cover_path = await self._save_cover(post)
                session.add(self._video(target.id, post, cover_path))
                new_count += 1
            await session.flush()
            if stop:
                break
        return new_count, updated_count

    async def _save_cover(self, post: ScrapedPost) -> str | None:
        if not post.cover_url:
            return None
        status, content = await self._media.fetch(post.cover_url)
        if status >= 400:
            return None
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
        video.updated_at = datetime.now(UTC)

    @staticmethod
    def _video(target_id: int, post: ScrapedPost, cover_path: str | None) -> DouyinVideo:
        return DouyinVideo(
            aweme_id=post.aweme_id, target_id=target_id, aweme_type=post.aweme_type,
            description=post.description, hashtags=post.hashtags, create_time=post.create_time,
            author_sec_uid=post.author_sec_uid, author_nickname=post.author_nickname,
            author_avatar=post.author_avatar, digg_count=post.digg_count,
            comment_count=post.comment_count, share_count=post.share_count,
            collect_count=post.collect_count, cover_remote_url=post.cover_url,
            cover_local_path=cover_path, raw_video_url=post.video_url, image_urls=post.image_urls,
        )
