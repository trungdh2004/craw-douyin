from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from enum import StrEnum
import logging
from pathlib import Path
import shutil
import sqlite3
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, TypeVar

from filelock import AsyncFileLock

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)
T = TypeVar("T")

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en', 'vi'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


def build_stealth_launch_kwargs(
    *,
    headless: bool = False,
    user_agent: str | None = None,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "headless": headless,
        "ignore_default_args": ["--enable-automation"],
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--disable-infobars",
        ],
    }
    chrome_bin = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    if chrome_bin:
        kwargs["executable_path"] = chrome_bin
    if user_agent:
        kwargs["user_agent"] = user_agent
    if proxy_url:
        kwargs["proxy"] = {"server": proxy_url}
    return kwargs


class BrowserSessionStatus(StrEnum):
    AUTHENTICATED = "AUTHENTICATED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    LOGIN_IN_PROGRESS = "LOGIN_IN_PROGRESS"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"


class DouyinBrowserAdapter(Protocol):
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus: ...

    async def open_login(self, profile_directory: Path) -> None: ...


class BrowserSessionManager:
    def __init__(
        self, adapter: DouyinBrowserAdapter, profile_directory: Path
    ) -> None:
        self._adapter = adapter
        self._profile_directory = profile_directory
        self._profile_lock = asyncio.Lock()
        self._process_lock = AsyncFileLock(
            profile_directory.with_name(f"{profile_directory.name}.lock")
        )
        self._login_task: asyncio.Task[None] | None = None
        self._captcha_required = False
        self._cached_status: BrowserSessionStatus | None = None
        self._cached_at: float = 0.0

    def mark_captcha_required(self) -> None:
        self._captcha_required = True

    async def get_status(self) -> BrowserSessionStatus:
        if self._login_task is not None and not self._login_task.done():
            return BrowserSessionStatus.LOGIN_IN_PROGRESS
        if self._captcha_required:
            return BrowserSessionStatus.CAPTCHA_REQUIRED
        now = time.monotonic()
        if self._cached_status is not None and (now - self._cached_at) < 2.0:
            return self._cached_status
        status = await self._adapter.get_status(self._profile_directory)
        self._cached_status = status
        self._cached_at = time.monotonic()
        return status

    async def run_with_profile(
        self, operation: Callable[[Path], Awaitable[T]]
    ) -> T:
        """Run background browser work without competing for the profile."""
        async with self._locked_profile():
            return await operation(self._profile_directory)

    def start_login(self) -> BrowserSessionStatus:
        if self._login_task is None or self._login_task.done():
            self._login_task = asyncio.create_task(self._run_login())
        return BrowserSessionStatus.LOGIN_IN_PROGRESS

    async def wait_for_login(self) -> None:
        if self._login_task is not None:
            await self._login_task

    async def close(self) -> None:
        if self._login_task is not None and not self._login_task.done():
            self._login_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._login_task

    async def _run_login(self) -> None:
        try:
            async with self._locked_profile():
                await self._adapter.open_login(self._profile_directory)
                self._captcha_required = False
                self._cached_status = None
                self._cached_at = 0.0
        except Exception:
            logger.exception("Error while running interactive Douyin login browser")
            self._cached_status = None
            self._cached_at = 0.0

    @asynccontextmanager
    async def _locked_profile(self) -> AsyncIterator[None]:
        async with self._profile_lock:
            async with self._process_lock:
                self._profile_directory.mkdir(parents=True, exist_ok=True)
                yield


class PlaywrightDouyinBrowserAdapter:
    _SESSION_COOKIE_NAMES = {"sessionid", "sessionid_ss", "sid_tt", "uid_tt"}

    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        if self._has_sqlite_session_cookies(profile_directory):
            return BrowserSessionStatus.AUTHENTICATED
        return BrowserSessionStatus.LOGIN_REQUIRED

    def _has_sqlite_session_cookies(self, profile_directory: Path) -> bool:
        candidates = [
            profile_directory / "Default" / "Cookies",
            profile_directory / "Cookies",
        ]
        for cookie_db in candidates:
            if not cookie_db.is_file():
                continue
            try:
                with sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True, timeout=2.0) as conn:
                    rows = conn.execute(
                        """
                        SELECT name FROM cookies
                        WHERE host_key LIKE '%douyin%'
                          AND name IN ('sessionid', 'sessionid_ss', 'sid_tt', 'uid_tt')
                          AND (length(value) > 0 OR length(encrypted_value) > 0)
                        LIMIT 1
                        """
                    ).fetchall()
                    if rows:
                        return True
            except sqlite3.Error:
                continue
        return False

    async def open_login(self, profile_directory: Path) -> None:
        async with self._browser_context(profile_directory, headless=False) as context:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(
                "https://www.douyin.com",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            # Tự động theo dõi trạng thái đăng nhập & Captcha để tự đóng trình duyệt khi hoàn tất
            while context.pages and not page.is_closed():
                await asyncio.sleep(1.5)
                if page.is_closed() or not context.pages:
                    break
                with suppress(Exception):
                    cookies = await context.cookies("https://www.douyin.com")
                    has_session = any(
                        c.get("name") in self._SESSION_COOKIE_NAMES and bool(c.get("value"))
                        for c in cookies
                    )
                    if has_session:
                        has_captcha = await page.locator(
                            "#captcha_container, .captcha_verify_container, [id*='captcha'], [class*='secsdk-captcha']"
                        ).count()
                        if has_captcha == 0:
                            await asyncio.sleep(1.5)
                            await context.close()
                            break

    @asynccontextmanager
    async def _browser_context(
        self, profile_directory: Path, *, headless: bool
    ) -> AsyncIterator[BrowserContext]:
        from playwright.async_api import BrowserContext, async_playwright

        launch_kwargs = build_stealth_launch_kwargs(headless=headless)
        async with async_playwright() as playwright:
            context: BrowserContext = await playwright.chromium.launch_persistent_context(
                str(profile_directory), **launch_kwargs
            )
            await context.add_init_script(STEALTH_INIT_SCRIPT)
            try:
                yield context
            finally:
                with suppress(Exception):
                    await context.close()


async def _cli_login() -> None:
    from douyin_crawler.settings import get_settings

    settings = get_settings()
    manager = BrowserSessionManager(
        adapter=PlaywrightDouyinBrowserAdapter(),
        profile_directory=settings.browser_profile_directory,
    )
    print(f"Đang mở trình duyệt Chromium (Profile: {settings.browser_profile_directory})...")
    print("Hãy quét mã QR đăng nhập Douyin hoặc giải Captcha, sau đó ĐÓNG cửa sổ trình duyệt để lưu phiên.")
    manager.start_login()
    await manager.wait_for_login()
    status = await manager.get_status()
    print(f"Đã đóng trình duyệt. Trạng thái phiên hiện tại: {status.value}")


if __name__ == "__main__":
    asyncio.run(_cli_login())
