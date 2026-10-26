from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Protocol, TypeVar

from filelock import AsyncFileLock

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

T = TypeVar("T")


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
        self._process_lock = AsyncFileLock(
            profile_directory.with_name(f"{profile_directory.name}.lock")
        )
        self._login_task: asyncio.Task[None] | None = None

    async def get_status(self) -> BrowserSessionStatus:
        if self._login_task is not None and not self._login_task.done():
            return BrowserSessionStatus.LOGIN_IN_PROGRESS
        async with self._locked_profile():
            return await self._adapter.get_status(self._profile_directory)

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
        async with self._locked_profile():
            await self._adapter.open_login(self._profile_directory)

    @asynccontextmanager
    async def _locked_profile(self) -> AsyncIterator[None]:
        async with self._profile_lock:
            async with self._process_lock:
                self._profile_directory.mkdir(parents=True, exist_ok=True)
                yield


class PlaywrightDouyinBrowserAdapter:
    _SESSION_COOKIE_NAMES = {"sessionid", "sessionid_ss", "sid_tt"}
    _ACCOUNT_INFO_URL = "https://www.douyin.com/passport/web/account/info/"

    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        from playwright.async_api import async_playwright

        async with self._browser_context(profile_directory, headless=True) as context:
            cookies = await context.cookies("https://www.douyin.com")
            cookie_names = {cookie["name"] for cookie in cookies}
            if not cookie_names & self._SESSION_COOKIE_NAMES:
                return BrowserSessionStatus.LOGIN_REQUIRED

            response = await context.request.get(self._ACCOUNT_INFO_URL)
            if not response.ok:
                return BrowserSessionStatus.LOGIN_REQUIRED
            payload = await response.json()
            account = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(account, dict) and account:
                return BrowserSessionStatus.AUTHENTICATED
            return BrowserSessionStatus.LOGIN_REQUIRED

    async def open_login(self, profile_directory: Path) -> None:
        from playwright.async_api import async_playwright

        async with self._browser_context(profile_directory, headless=False) as context:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://www.douyin.com", wait_until="domcontentloaded")
            await context.wait_for_event("close")

    @asynccontextmanager
    async def _browser_context(
        self, profile_directory: Path, *, headless: bool
    ) -> AsyncIterator[BrowserContext]:
        from playwright.async_api import BrowserContext, async_playwright

        async with async_playwright() as playwright:
            context: BrowserContext = await playwright.chromium.launch_persistent_context(
                str(profile_directory), headless=headless
            )
            try:
                yield context
            finally:
                if context.pages:
                    await context.close()
