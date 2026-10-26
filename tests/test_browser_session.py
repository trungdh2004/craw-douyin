import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.main import create_app


class FakeDouyinBrowserAdapter:
    def __init__(self) -> None:
        self.authenticated = False
        self.login_calls: list[Path] = []

    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return (
            BrowserSessionStatus.AUTHENTICATED
            if self.authenticated
            else BrowserSessionStatus.LOGIN_REQUIRED
        )

    async def open_login(self, profile_directory: Path) -> None:
        self.login_calls.append(profile_directory)
        self.authenticated = True


class BlockingBrowserAdapter(FakeDouyinBrowserAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.login_started = asyncio.Event()
        self.close_login = asyncio.Event()

    async def open_login(self, profile_directory: Path) -> None:
        self.login_calls.append(profile_directory)
        self.login_started.set()
        await self.close_login.wait()
        self.authenticated = True


class PersistentProfileBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        if (profile_directory / "authenticated").exists():
            return BrowserSessionStatus.AUTHENTICATED
        return BrowserSessionStatus.LOGIN_REQUIRED

    async def open_login(self, profile_directory: Path) -> None:
        (profile_directory / "authenticated").touch()


async def test_operator_can_check_session_and_open_login_browser(tmp_path: Path) -> None:
    adapter = FakeDouyinBrowserAdapter()
    profile_directory = tmp_path / "browser-profile"
    app = create_app(
        browser_adapter=adapter,
        browser_profile_directory=profile_directory,
        start_scheduler=False,
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            initial_status = await client.get("/api/browser/status")
            login_response = await client.post("/api/browser/login")
            await app.state.browser_session.wait_for_login()
            authenticated_status = await client.get("/api/browser/status")

    assert initial_status.json() == {"status": "LOGIN_REQUIRED"}
    assert login_response.status_code == 202
    assert login_response.json() == {"status": "LOGIN_IN_PROGRESS"}
    assert authenticated_status.json() == {"status": "AUTHENTICATED"}
    assert adapter.login_calls == [profile_directory]


async def test_dashboard_exposes_browser_session_controls() -> None:
    app = create_app(start_scheduler=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")

    assert "Trạng thái đăng nhập Douyin" in response.text
    assert "/api/browser/status" in response.text
    assert "/api/browser/login" in response.text


async def test_requests_sharing_profile_do_not_open_competing_browsers(
    tmp_path: Path,
) -> None:
    adapter = BlockingBrowserAdapter()
    app = create_app(
        browser_adapter=adapter,
        browser_profile_directory=tmp_path / "profile",
        start_scheduler=False,
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_login = await client.post("/api/browser/login")
            await adapter.login_started.wait()
            second_login = await client.post("/api/browser/login")
            status_while_open = await client.get("/api/browser/status")
            adapter.close_login.set()
            await app.state.browser_session.wait_for_login()

    assert first_login.status_code == 202
    assert second_login.status_code == 202
    assert status_while_open.json() == {"status": "LOGIN_IN_PROGRESS"}
    assert adapter.login_calls == [tmp_path / "profile"]


async def test_login_session_is_reused_after_application_restart(tmp_path: Path) -> None:
    profile_directory = tmp_path / "persistent-profile"
    first_app = create_app(
        browser_adapter=PersistentProfileBrowserAdapter(),
        browser_profile_directory=profile_directory,
        start_scheduler=False,
    )
    async with first_app.router.lifespan_context(first_app):
        async with AsyncClient(
            transport=ASGITransport(app=first_app), base_url="http://test"
        ) as client:
            await client.post("/api/browser/login")
            await first_app.state.browser_session.wait_for_login()

    restarted_app = create_app(
        browser_adapter=PersistentProfileBrowserAdapter(),
        browser_profile_directory=profile_directory,
        start_scheduler=False,
    )
    async with restarted_app.router.lifespan_context(restarted_app):
        async with AsyncClient(
            transport=ASGITransport(app=restarted_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/browser/status")

    assert response.json() == {"status": "AUTHENTICATED"}
