from __future__ import annotations

import asyncio
import inspect
import json
import random
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, unquote

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from douyin_crawler.anti_bot import PRESET_DEFAULTS, get_or_create_anti_bot_settings
from douyin_crawler.browser import (
    STEALTH_INIT_SCRIPT,
    BrowserSessionManager,
    build_stealth_launch_kwargs,
)
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


LogEventCallback = Callable[[str, str, str], Awaitable[None]]


def _print_terminal_log(log_id: int, label: str, level: str, step: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    color = {
        "SUCCESS": "\033[92m",
        "WARN": "\033[93m",
        "ERROR": "\033[91m",
        "INFO": "\033[96m",
    }.get(level, "\033[0m")
    reset = "\033[0m"
    print(
        f"{color}[{ts}] [Phiên #{log_id} | {label}] [{step}]{reset} {message}",
        flush=True,
    )


class DouyinContentAdapter(Protocol):
    def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]: ...

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost: ...


class MediaHttpAdapter(Protocol):
    async def fetch(self, url: str) -> tuple[int, bytes]: ...


class HttpxMediaAdapter:
    async def fetch(self, url: str) -> tuple[int, bytes]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=180) as client:
            response = await client.get(
                url,
                headers={
                    "Referer": "https://www.douyin.com/",
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
            )
            return response.status_code, response.content


class PlaywrightDouyinContentAdapter:
    _CAPTCHA_SELECTOR = (
        "#captcha_container, .captcha_verify_container, .secsdk-captcha-drag-icon"
    )

    def __init__(self, sessions: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sessions = sessions

    async def _load_anti_bot(self) -> dict[str, Any]:
        if self._sessions is None:
            return {
                **PRESET_DEFAULTS["BALANCED"],
                "headless_mode": False,
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
                "headless_mode": cfg.headless_mode,
                "max_pages_per_run": cfg.max_pages_per_run,
                "user_agent": cfg.user_agent,
                "proxy_url": cfg.proxy_url,
            }

    async def _wait_if_captcha_visible(
        self,
        page: Any,
        *,
        auto_stop: bool,
        on_event: LogEventCallback | None = None,
    ) -> None:
        try:
            visible = await page.locator(self._CAPTCHA_SELECTOR).first.is_visible()
        except Exception:
            visible = False
        if not visible:
            return
        if on_event is not None:
            await on_event(
                "WARN",
                "CAPTCHA",
                "Phát hiện khung Captcha trên màn hình Chrome! Đang chờ bạn kéo giải Captcha (tối đa 45s)...",
            )
        # Cho phép người dùng kéo giải Captcha ngay trên cửa sổ đang mở trong tối đa 45s
        for _ in range(30):
            await page.wait_for_timeout(1500)
            try:
                still_visible = await page.locator(self._CAPTCHA_SELECTOR).first.is_visible()
            except Exception:
                still_visible = False
            if not still_visible:
                if on_event is not None:
                    await on_event(
                        "SUCCESS",
                        "CAPTCHA",
                        "Đã giải xong Captcha! Tiếp tục quá trình thu thập dữ liệu...",
                    )
                return
        if auto_stop:
            raise CaptchaDetectedError("Douyin yêu cầu giải Captcha xác thực (quá 45s chưa giải)")

    async def _scroll_feed(
        self,
        page: Any,
        *,
        human_scroll: bool,
        scroll_index: int = 1,
        on_event: LogEventCallback | None = None,
    ) -> None:
        try:
            await page.mouse.move(
                680 + random.randint(-40, 40),
                500 + random.randint(-40, 40),
            )
        except Exception:
            pass
        steps = (650, 750, 600) if human_scroll else (1800,)
        total_dy = 0
        for step in steps:
            delta = step + (random.randint(-80, 120) if human_scroll else 0)
            total_dy += delta
            try:
                await page.mouse.wheel(0, delta)
            except Exception:
                pass
            try:
                await page.evaluate(
                    """(dy) => {
                        window.scrollBy({ top: dy, behavior: 'smooth' });
                        if (document.scrollingElement) {
                            document.scrollingElement.scrollTop += dy;
                        }
                        const candidates = document.querySelectorAll(
                            '#douyin-right-container, [data-e2e="scroll-list"], .route-scroll-container, main, div'
                        );
                        for (const el of candidates) {
                            if (el.clientWidth > 320 && el.scrollHeight > el.clientHeight + 150) {
                                const style = window.getComputedStyle(el);
                                if (style.overflowY === 'auto' || style.overflowY === 'scroll' || el.id === 'douyin-right-container') {
                                    el.scrollTop += dy;
                                }
                            }
                        }
                    }""",
                    delta,
                )
            except Exception:
                pass
            if human_scroll:
                await page.wait_for_timeout(random.randint(180, 350))
        if on_event is not None:
            await on_event(
                "INFO",
                "SCROLL",
                f"Đã cuộn trang nhịp #{scroll_index} (tổng dy={total_dy}px trên #douyin-right-container)",
            )

    async def crawl(
        self,
        profile: Path,
        target: CrawlTarget,
        on_event: LogEventCallback | None = None,
    ) -> AsyncIterator[list[ScrapedPost]]:
        from playwright.async_api import async_playwright

        cfg = await self._load_anti_bot()
        queue: asyncio.Queue[list[ScrapedPost]] = asyncio.Queue()
        endpoints: tuple[str, ...]
        if target.target_type == "CHANNEL":
            endpoints = ("aweme/post",)
        elif target.target_type == "COLLECT":
            endpoints = ("listcollection", "aweme/favorite")
        else:
            endpoints = ("general/search", "search/item", "search/single", "discover/search")
        is_headless = bool(cfg.get("headless_mode", False))
        launch_kwargs = build_stealth_launch_kwargs(
            headless=is_headless,
            user_agent=cfg.get("user_agent"),
            proxy_url=cfg.get("proxy_url"),
        )
        if on_event is not None:
            await on_event(
                "INFO",
                "BROWSER",
                f"Mở trình duyệt Chrome thật (Headless={is_headless}, Stealth={cfg.get('stealth_mode')}, HumanScroll={cfg.get('human_scroll')}, Delay={cfg.get('scroll_delay_min_ms')}..{cfg.get('scroll_delay_max_ms')}ms)",
            )
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(profile), **launch_kwargs
            )
            if cfg.get("stealth_mode", True):
                await context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.pages[0] if context.pages else await context.new_page()
            api_batch_counter = 0

            async def capture(response: Any) -> None:
                nonlocal api_batch_counter
                matched_ep = next((ep for ep in endpoints if ep in response.url), None)
                if not matched_ep:
                    return
                try:
                    payload = await response.json()
                    raw_posts = payload.get("aweme_list") or payload.get("data") or []
                    extracted: list[dict[str, Any]] = []
                    for entry in raw_posts:
                        if not isinstance(entry, dict):
                            continue
                        if entry.get("aweme_id"):
                            extracted.append(entry)
                        elif (
                            isinstance(entry.get("aweme_info"), dict)
                            and entry["aweme_info"].get("aweme_id")
                        ):
                            extracted.append(entry["aweme_info"])
                        elif isinstance(entry.get("aweme_mix_info"), dict):
                            for mix_item in entry["aweme_mix_info"].get("mix_items") or []:
                                if isinstance(mix_item, dict) and mix_item.get("aweme_id"):
                                    extracted.append(mix_item)
                    posts = [self._normalize(item) for item in extracted]
                    if posts:
                        api_batch_counter += 1
                        if on_event is not None:
                            await on_event(
                                "SUCCESS",
                                "API",
                                f"Bắt được gói dữ liệu #{api_batch_counter} từ API '{matched_ep}': chứa {len(posts)} bài đăng",
                            )
                        await queue.put(posts)
                except Exception:
                    return

            context.on("response", lambda response: asyncio.create_task(capture(response)))
            url = self._target_url(target)
            try:
                if target.target_type == "KEYWORD" and not target.target_value.startswith("http"):
                    if on_event is not None:
                        await on_event(
                            "INFO",
                            "NAVIGATE",
                            f"Truy cập trang chủ https://www.douyin.com/jingxuan để tìm từ khóa '{target.target_value}'...",
                        )
                    await page.goto(
                        "https://www.douyin.com/jingxuan",
                        wait_until="domcontentloaded",
                        timeout=45_000,
                    )
                    await page.wait_for_timeout(random.randint(1000, 1600))
                    search_input = page.locator(
                        'input[data-e2e="searchbar-input"], input[type="text"]'
                    ).first
                    if await search_input.count() > 0 and await search_input.is_visible():
                        await search_input.click()
                        await search_input.fill(target.target_value)
                        await page.wait_for_timeout(random.randint(300, 500))
                        search_btn = page.locator('[data-e2e="searchbar-button"]').first
                        if await search_btn.count() > 0 and await search_btn.is_visible():
                            await search_btn.click()
                        else:
                            await search_input.press("Enter")
                        await page.wait_for_timeout(2500)
                        if len(context.pages) > 1:
                            page = context.pages[-1]
                            await page.bring_to_front()
                        if on_event is not None:
                            await on_event(
                                "INFO",
                                "NAVIGATE",
                                f"Đã chuyển tới trang kết quả tìm kiếm: {page.url}",
                            )
                    if "search" not in page.url:
                        if on_event is not None:
                            await on_event(
                                "INFO",
                                "NAVIGATE",
                                f"Điều hướng trực tiếp tới URL tìm kiếm: {url}",
                            )
                        await page.goto(
                            url,
                            referer="https://www.douyin.com/jingxuan",
                            wait_until="domcontentloaded",
                        )
                else:
                    if on_event is not None:
                        await on_event(
                            "INFO",
                            "NAVIGATE",
                            f"Mở trang mục tiêu ({target.target_type}): {url}",
                        )
                    await page.goto(
                        url,
                        referer="https://www.douyin.com/jingxuan",
                        wait_until="domcontentloaded",
                    )

                pages = 0
                scroll_counter = 0
                max_pages = max(
                    int(cfg.get("max_pages_per_run", 25)),
                    (target.max_items_per_run // 6) + 8,
                )
                while pages < max_pages:
                    if len(context.pages) > 1 and page != context.pages[-1]:
                        page = context.pages[-1]
                    await self._wait_if_captcha_visible(
                        page,
                        auto_stop=bool(cfg.get("auto_stop_on_captcha", True)),
                        on_event=on_event,
                    )
                    posts: list[ScrapedPost] | None = None
                    # Nếu hàng đợi chưa có batch mới, liên tục cuộn xuống để kích hoạt tải thêm
                    for _scroll_try in range(8):
                        try:
                            posts = await asyncio.wait_for(queue.get(), timeout=2.2)
                            break
                        except TimeoutError:
                            await self._wait_if_captcha_visible(
                                page,
                                auto_stop=bool(cfg.get("auto_stop_on_captcha", True)),
                                on_event=on_event,
                            )
                            scroll_counter += 1
                            await self._scroll_feed(
                                page,
                                human_scroll=bool(cfg.get("human_scroll", True)),
                                scroll_index=scroll_counter,
                                on_event=on_event,
                            )
                            delay_ms = random.randint(
                                int(cfg.get("scroll_delay_min_ms", 1200)),
                                int(cfg.get("scroll_delay_max_ms", 2500)),
                            )
                            await page.wait_for_timeout(delay_ms)
                    if not posts:
                        if on_event is not None:
                            await on_event(
                                "WARN",
                                "SCROLL",
                                "Đã cuộn 8 nhịp liên tiếp nhưng Douyin không trả thêm bài mới (đã hết danh sách hoặc bị giới hạn).",
                            )
                        break
                    yield posts
                    pages += 1
                    # Nghỉ nhịp tự nhiên (Micro-batch pacing) mỗi 2 đợt để tránh bị Captcha
                    if pages % 2 == 0:
                        cooldown_ms = random.randint(2500, 4500)
                        if on_event is not None:
                            await on_event(
                                "INFO",
                                "COOLDOWN",
                                f"Tạm nghỉ Cooldown {cooldown_ms}ms sau {pages} đợt API để tránh Captcha...",
                            )
                        await page.wait_for_timeout(cooldown_ms)
                    # Cuộn xuống ngay sau khi nhận batch để chuẩn bị trang kế tiếp
                    scroll_counter += 1
                    await self._scroll_feed(
                        page,
                        human_scroll=bool(cfg.get("human_scroll", True)),
                        scroll_index=scroll_counter,
                        on_event=on_event,
                    )
                    delay_ms = random.randint(
                        int(cfg.get("scroll_delay_min_ms", 1200)),
                        int(cfg.get("scroll_delay_max_ms", 2500)),
                    )
                    await page.wait_for_timeout(delay_ms)
            finally:
                await context.close()

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        from playwright.async_api import async_playwright

        cfg = await self._load_anti_bot()
        launch_kwargs = build_stealth_launch_kwargs(
            headless=bool(cfg.get("headless_mode", False)),
            user_agent=cfg.get("user_agent"),
            proxy_url=cfg.get("proxy_url"),
        )
        result: asyncio.Future[ScrapedPost] = asyncio.get_running_loop().create_future()
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(profile), **launch_kwargs
            )
            if cfg.get("stealth_mode", True):
                await context.add_init_script(STEALTH_INIT_SCRIPT)
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

            context.on("response", lambda response: asyncio.create_task(capture(response)))
            target_url = (
                aweme_id
                if aweme_id.startswith("http")
                else f"https://www.douyin.com/jingxuan?modal_id={aweme_id}"
            )
            try:
                await page.goto(
                    target_url,
                    referer="https://www.douyin.com/jingxuan",
                    wait_until="domcontentloaded",
                )
                await self._wait_if_captcha_visible(page, auto_stop=False)
                if result.done():
                    return result.result()
                for _ in range(3):
                    try:
                        html = await page.content()
                        ssr_post = self._extract_ssr_video_detail(html)
                        if ssr_post is not None and ssr_post.video_url:
                            return ssr_post
                    except Exception:
                        pass
                    try:
                        return await asyncio.wait_for(asyncio.shield(result), timeout=1.2)
                    except TimeoutError:
                        continue
                return await asyncio.wait_for(result, timeout=12)
            finally:
                await context.close()

    @classmethod
    def _extract_ssr_video_detail(cls, html: str) -> ScrapedPost | None:
        unquoted = unquote(html)
        for match in re.finditer(r'"videoDetail":(\{)', unquoted):
            try:
                item, _ = json.JSONDecoder().raw_decode(unquoted[match.start(1) :])
                if isinstance(item, dict) and (item.get("awemeId") or item.get("aweme_id")):
                    return cls._normalize(item)
            except Exception:
                continue
        return None

    @staticmethod
    def _target_url(target: CrawlTarget) -> str:
        if target.target_type == "KEYWORD":
            if target.target_value.startswith("http"):
                return target.target_value
            return (
                f"https://www.douyin.com/jingxuan/search/{quote(target.target_value)}?type=general"
            )
        if target.target_type == "COLLECT":
            if target.target_value.startswith("http"):
                return target.target_value
            return "https://www.douyin.com/user/self?showTab=favorite_collection"
        if target.target_value.startswith("http"):
            return target.target_value
        return f"https://www.douyin.com/user/{target.target_value}"

    @staticmethod
    def _normalize(item: dict[str, Any]) -> ScrapedPost:
        author = item.get("author") or item.get("authorInfo") or {}
        statistics = item.get("statistics") or item.get("stats") or {}
        video = item.get("video") or {}
        music = item.get("music") or {}
        raw_cover = video.get("cover")
        cover = raw_cover if isinstance(raw_cover, dict) else {}
        play = video.get("play_addr") or {}
        play_addr_list = video.get("playAddr") if isinstance(video.get("playAddr"), list) else []
        images = item.get("images") or []
        raw_duration = video.get("duration") or item.get("duration") or 0
        width = video.get("width")
        height = video.get("height")
        text_extra = item.get("text_extra") or item.get("textExtra") or []
        avatar_thumb = author.get("avatar_thumb") or author.get("avatarThumb") or {}
        author_avatar = (
            (avatar_thumb.get("url_list") or avatar_thumb.get("urlList") or [None])[0]
            if isinstance(avatar_thumb, dict)
            else None
        ) or author.get("avatarUri")
        cover_url = (
            raw_cover
            if isinstance(raw_cover, str) and raw_cover
            else (
                (cover.get("url_list") or cover.get("urlList") or video.get("coverUrlList") or [None])[0]
            )
        )
        video_url = (play.get("url_list") or [None])[0]
        if not video_url and play_addr_list:
            first_play = play_addr_list[0]
            if isinstance(first_play, dict):
                video_url = first_play.get("src")
            elif isinstance(first_play, str):
                video_url = first_play
        image_urls: list[str] = []
        for image in images:
            if isinstance(image, dict):
                urls = image.get("url_list") or image.get("urlList") or []
                if urls:
                    image_urls.append(str(urls[0]))
        return ScrapedPost(
            aweme_id=str(item.get("aweme_id") or item.get("awemeId")),
            aweme_type=int(item.get("aweme_type", item.get("awemeType", 0)) or 0),
            description=item.get("desc") or "",
            hashtags=[
                str(entry.get("hashtag_name") or entry.get("hashtagName"))
                for entry in text_extra
                if isinstance(entry, dict) and (entry.get("hashtag_name") or entry.get("hashtagName"))
            ],
            create_time=datetime.fromtimestamp(
                int(item.get("create_time") or item.get("createTime") or 0), UTC
            ),
            author_sec_uid=author.get("sec_uid") or author.get("secUid") or "",
            author_nickname=author.get("nickname") or "",
            author_avatar=author_avatar,
            digg_count=int(statistics.get("digg_count", statistics.get("diggCount", 0)) or 0),
            comment_count=int(statistics.get("comment_count", statistics.get("commentCount", 0)) or 0),
            share_count=int(statistics.get("share_count", statistics.get("shareCount", 0)) or 0),
            collect_count=int(statistics.get("collect_count", statistics.get("collectCount", 0)) or 0),
            cover_url=cover_url,
            video_url=video_url,
            image_urls=image_urls,
            is_top=bool(item.get("is_top", item.get("isTop", 0))),
            duration_ms=int(raw_duration),
            width=int(width) if width is not None else None,
            height=int(height) if height is not None else None,
            music_title=music.get("title") or music.get("musicName"),
            music_author=music.get("author") or music.get("ownerNickname"),
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

    async def _record_event(
        self,
        session: AsyncSession,
        log: CrawlLog,
        label: str,
        level: str,
        step: str,
        message: str,
        *,
        scanned_count: int | None = None,
        new_count: int | None = None,
        updated_count: int | None = None,
        commit: bool = True,
    ) -> None:
        _print_terminal_log(log.id or 0, label, level, step, message)
        payload = dict(log.payload or {})
        events = list(payload.get("events") or [])
        events.append(
            {
                "ts": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "step": step,
                "message": message,
            }
        )
        if len(events) > 300:
            events = events[-300:]
        payload["events"] = events
        payload["current_phase"] = f"[{step}] {message}"
        if scanned_count is not None:
            payload["scanned_count"] = scanned_count
        if new_count is not None:
            log.new_videos_count = new_count
        if updated_count is not None:
            log.updated_videos_count = updated_count
        log.payload = payload
        flag_modified(log, "payload")
        if commit:
            await session.commit()

    async def run(self, target_id: int, trigger_type: str = "MANUAL") -> None:
        new_ids: list[str] = []
        auto_download = False
        async with self._sessions() as session:
            target = await session.get(CrawlTarget, target_id)
            if target is None:
                return
            auto_download = target.auto_download
            label = f"{target.target_type}: {target.name}"
            log = CrawlLog(
                target_id=target_id,
                job_type="TARGET_CRAWL",
                trigger_type=trigger_type,
                input_summary=label,
                payload={
                    "target_id": target_id,
                    "target_limit": target.max_items_per_run,
                    "scanned_count": 0,
                    "current_phase": "Đang khởi tạo phiên quét...",
                    "events": [],
                },
                status="RUNNING",
            )
            target.last_status = "RUNNING"
            session.add(log)
            await session.commit()
            await session.refresh(log)
            await self._record_event(
                session,
                log,
                label,
                "INFO",
                "START",
                f"Bắt đầu phiên quét '{target.name}' (Loại={target.target_type}, Giá trị='{target.target_value}', Mục tiêu cần lấy={target.max_items_per_run} bài mới)",
            )
            try:
                counts, new_ids = await self._browser.run_with_profile(
                    lambda profile: self._crawl(session, target, profile, log=log)
                )
                log.new_videos_count, log.updated_videos_count = counts
                log.status = target.last_status = "SUCCESS"
                scanned_total = int((log.payload or {}).get("scanned_count") or 0)
                await self._record_event(
                    session,
                    log,
                    label,
                    "SUCCESS",
                    "DONE",
                    f"Hoàn tất thành công! Đã thu thập +{counts[0]} bài mới, cập nhật {counts[1]} bài đã cào trước đó (tổng quét qua {scanned_total} bài).",
                    new_count=counts[0],
                    updated_count=counts[1],
                    commit=False,
                )
            except CaptchaDetectedError as error:
                log.status = "CAPTCHA_BLOCKED"
                target.last_status = "FAILED"
                log.error_message = str(error)
                self._browser.mark_captcha_required()
                await self._record_event(
                    session,
                    log,
                    label,
                    "ERROR",
                    "CAPTCHA",
                    f"Phiên quét tạm dừng do Captcha: {error}",
                    commit=False,
                )
            except Exception as error:
                log.status = target.last_status = "FAILED"
                log.error_message = str(error)
                await self._record_event(
                    session,
                    log,
                    label,
                    "ERROR",
                    "ERROR",
                    f"Lỗi trong quá trình quét: {error}",
                    commit=False,
                )
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
            label = log.input_summary or f"Crawl lẻ ({len(inputs)} mục)"
            log.status = "RUNNING"
            log.started_at = datetime.now(UTC)
            payload = dict(log.payload or {})
            payload.setdefault("target_limit", len(inputs))
            payload.setdefault("scanned_count", 0)
            payload.setdefault("events", [])
            log.payload = payload
            flag_modified(log, "payload")
            await session.commit()
            await self._record_event(
                session,
                log,
                label,
                "INFO",
                "START",
                f"Bắt đầu Crawl {len(inputs)} ID / Link chia sẻ (Tự tải={auto_download}, Bookmark={is_bookmarked})",
            )
            try:
                new_count, updated_count, crawled_ids = await self._browser.run_with_profile(
                    lambda profile: self._crawl_items(
                        session,
                        profile,
                        inputs,
                        is_bookmarked=is_bookmarked,
                        bookmark_collection=bookmark_collection,
                        log=log,
                    )
                )
                log.new_videos_count = new_count
                log.updated_videos_count = updated_count
                log.status = "SUCCESS"
                await self._record_event(
                    session,
                    log,
                    label,
                    "SUCCESS",
                    "DONE",
                    f"Hoàn tất Crawl lẻ: +{new_count} bài mới, {updated_count} bài cập nhật.",
                    new_count=new_count,
                    updated_count=updated_count,
                    commit=False,
                )
            except CaptchaDetectedError as error:
                log.status = "CAPTCHA_BLOCKED"
                log.error_message = str(error)
                self._browser.mark_captcha_required()
                await self._record_event(
                    session,
                    log,
                    label,
                    "ERROR",
                    "CAPTCHA",
                    f"Bị chặn bởi Captcha: {error}",
                    commit=False,
                )
            except Exception as error:
                log.status = "FAILED"
                log.error_message = str(error)
                await self._record_event(
                    session,
                    log,
                    label,
                    "ERROR",
                    "ERROR",
                    f"Lỗi khi Crawl ID/Link: {error}",
                    commit=False,
                )
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
        log: CrawlLog | None = None,
    ) -> tuple[int, int, list[str]]:
        new_count = updated_count = scanned = 0
        crawled_ids: list[str] = []
        label = (log.input_summary if log else None) or "Crawl lẻ"
        for raw in inputs:
            token = parse_douyin_identifier(raw)
            if not token:
                continue
            scanned += 1
            if log is not None:
                await self._record_event(
                    session,
                    log,
                    label,
                    "INFO",
                    "DETAIL",
                    f"Đang mở Chrome lấy chi tiết bài #{scanned}/{len(inputs)}: '{token}'...",
                    scanned_count=scanned,
                )
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
                if log is not None:
                    await self._record_event(
                        session,
                        log,
                        label,
                        "INFO",
                        "VIDEO_SKIP",
                        f"[ĐÃ CÓ] ID {post.aweme_id} (@{post.author_nickname}) -> Cập nhật chỉ số (❤ {post.digg_count})",
                        scanned_count=scanned,
                        new_count=new_count,
                        updated_count=updated_count,
                    )
            else:
                cover_path = await self._save_cover(post)
                video = self._video(None, post, cover_path)
                if is_bookmarked:
                    video.is_bookmarked = True
                    video.bookmarked_at = datetime.now(UTC)
                    video.bookmark_collection = bookmark_collection
                session.add(video)
                new_count += 1
                if log is not None:
                    await self._record_event(
                        session,
                        log,
                        label,
                        "SUCCESS",
                        "VIDEO_NEW",
                        f"[+BÀI MỚI] ID {post.aweme_id} (@{post.author_nickname}) - \"{(post.description or '')[:45]}\" ({post.duration_ms // 1000}s)",
                        scanned_count=scanned,
                        new_count=new_count,
                        updated_count=updated_count,
                    )
            crawled_ids.append(post.aweme_id)
            await session.flush()
        return new_count, updated_count, crawled_ids

    async def _crawl(
        self,
        session: AsyncSession,
        target: CrawlTarget,
        profile: Path,
        *,
        log: CrawlLog | None = None,
    ) -> tuple[tuple[int, int], list[str]]:
        new_count = updated_count = scanned = consecutive_existing = 0
        new_ids: list[str] = []
        stop = False
        label = f"{target.target_type}: {target.name}"
        max_scan_limit = max(target.max_items_per_run * 8, 200)

        async def handle_adapter_event(level: str, step: str, message: str) -> None:
            if log is not None:
                await self._record_event(
                    session,
                    log,
                    label,
                    level,
                    step,
                    message,
                    scanned_count=scanned,
                    new_count=new_count,
                    updated_count=updated_count,
                )

        crawl_fn = self._content.crawl
        if "on_event" in inspect.signature(crawl_fn).parameters:
            stream = crawl_fn(profile, target, on_event=handle_adapter_event)  # type: ignore[call-arg]
        else:
            stream = crawl_fn(profile, target)

        async for page in stream:
            for post in page:
                if new_count >= target.max_items_per_run or scanned >= max_scan_limit:
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
                    if log is not None:
                        await self._record_event(
                            session,
                            log,
                            label,
                            "INFO",
                            "VIDEO_SKIP",
                            f"[ĐÃ CÀO - BỎ QUA #{updated_count}] ID {post.aweme_id} (@{post.author_nickname}) -> Cập nhật ❤ {post.digg_count}, tiếp tục cuộn tìm bài mới (Tiến độ: {new_count}/{target.max_items_per_run} mới, đã quét {scanned} bài)",
                            scanned_count=scanned,
                            new_count=new_count,
                            updated_count=updated_count,
                            commit=True,
                        )
                    if target.target_type == "CHANNEL" and not post.is_top:
                        consecutive_existing += 1
                        if consecutive_existing >= 3:
                            if log is not None:
                                await self._record_event(
                                    session,
                                    log,
                                    label,
                                    "INFO",
                                    "CHANNEL_SYNC",
                                    "Đã gặp 3 bài không ghim liên tiếp có sẵn trong kho -> Kênh đã đồng bộ tới bài mới nhất.",
                                    scanned_count=scanned,
                                    new_count=new_count,
                                    updated_count=updated_count,
                                    commit=True,
                                )
                            stop = True
                            break
                    continue
                consecutive_existing = 0
                try:
                    cover_path = await self._save_cover(post)
                except Exception:
                    cover_path = None
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
                if log is not None:
                    desc_short = (post.description or "(Không tiêu đề)").replace("\n", " ")[:48]
                    await self._record_event(
                        session,
                        log,
                        label,
                        "SUCCESS",
                        "VIDEO_NEW",
                        f"[+BÀI MỚI {new_count}/{target.max_items_per_run}] ID {post.aweme_id} (@{post.author_nickname}) - \"{desc_short}\" ({post.duration_ms // 1000}s, ❤ {post.digg_count})",
                        scanned_count=scanned,
                        new_count=new_count,
                        updated_count=updated_count,
                        commit=True,
                    )
                else:
                    await session.commit()
            await session.commit()
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
