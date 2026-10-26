import asyncio
from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class BrowserSessionStatus(StrEnum):
    AUTHENTICATED = "AUTHENTICATED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    LOGIN_IN_PROGRESS = "LOGIN_IN_PROGRESS"


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
        self._login_task: asyncio.Task[None] | None = None

    async def get_status(self) -> BrowserSessionStatus:
        if self._login_task is not None and not self._login_task.done():
            return BrowserSessionStatus.LOGIN_IN_PROGRESS
        async with self._profile_lock:
            return await self._adapter.get_status(self._profile_directory)

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
        async with self._profile_lock:
            self._profile_directory.mkdir(parents=True, exist_ok=True)
            await self._adapter.open_login(self._profile_directory)


class PlaywrightDouyinBrowserAdapter:
    _SESSION_COOKIE_NAMES = {"sessionid", "sessionid_ss", "sid_tt"}

    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        from playwright.async_api import async_playwright

        profile_directory.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(profile_directory), headless=True
            )
            try:
                cookies = await context.cookies("https://www.douyin.com")
            finally:
                await context.close()

        cookie_names = {cookie["name"] for cookie in cookies}
        if cookie_names & self._SESSION_COOKIE_NAMES:
            return BrowserSessionStatus.AUTHENTICATED
        return BrowserSessionStatus.LOGIN_REQUIRED

    async def open_login(self, profile_directory: Path) -> None:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(profile_directory), headless=False
            )
            try:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto("https://www.douyin.com", wait_until="domcontentloaded")
                await context.wait_for_event("close")
            finally:
                if context.pages:
                    await context.close()
