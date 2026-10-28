import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.main import create_app


class StubBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return BrowserSessionStatus.AUTHENTICATED

    async def open_login(self, profile_directory: Path) -> None:
        return None


async def test_admin_authentication_login_password_change_and_logout(tmp_path: Path) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=StubBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
            require_auth=True,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # 1. Public healthcheck and auth status work without auth
                health = await client.get("/api/health")
                assert health.status_code == 200

                status_before = await client.get("/api/auth/status")
                assert status_before.status_code == 200
                assert status_before.json() == {
                    "authenticated": False,
                    "username": None,
                }

                # 2. Protected management API returns 401 when unauthenticated
                unauth_stats = await client.get("/api/stats")
                assert unauth_stats.status_code == 401

                # 3. Wrong password returns 401
                bad_login = await client.post(
                    "/api/auth/login",
                    json={"username": "admin", "password": "wrong-password"},
                )
                assert bad_login.status_code == 401

                # 4. Correct default login succeeds and sets session-only cookie
                login_res = await client.post(
                    "/api/auth/login",
                    json={"username": "admin", "password": "admin123"},
                )
                assert login_res.status_code == 200
                body = login_res.json()
                assert body["authenticated"] is True
                assert body["username"] == "admin"
                assert isinstance(body["token"], str) and len(body["token"]) > 10
                set_cookie_header = login_res.headers.get("set-cookie", "")
                assert "douyin_session=" in set_cookie_header
                assert "Max-Age=" not in set_cookie_header

                # 5. Authenticated requests now succeed
                auth_stats = await client.get("/api/stats")
                assert auth_stats.status_code == 200

                status_after = await client.get("/api/auth/status")
                assert status_after.json() == {
                    "authenticated": True,
                    "username": "admin",
                }

                # 6. Changing password with wrong current_password fails
                bad_pw_change = await client.put(
                    "/api/auth/password",
                    json={
                        "current_password": "wrong",
                        "new_username": "trungadmin",
                        "new_password": "new-secret-password",
                    },
                )
                assert bad_pw_change.status_code == 400

                # 7. Changing username & password with valid current_password succeeds
                ok_pw_change = await client.put(
                    "/api/auth/password",
                    json={
                        "current_password": "admin123",
                        "new_username": "trungadmin",
                        "new_password": "new-secret-password",
                    },
                )
                assert ok_pw_change.status_code == 200
                assert ok_pw_change.json()["username"] == "trungadmin"

                # 8. Logout clears session and blocks subsequent /api/stats calls
                logout_res = await client.post("/api/auth/logout")
                assert logout_res.status_code == 200
                assert logout_res.json()["authenticated"] is False

                stats_after_logout = await client.get("/api/stats")
                assert stats_after_logout.status_code == 401

                # 9. Old credentials no longer work; new credentials work
                old_login = await client.post(
                    "/api/auth/login",
                    json={"username": "admin", "password": "admin123"},
                )
                assert old_login.status_code == 401

                new_login = await client.post(
                    "/api/auth/login",
                    json={"username": "trungadmin", "password": "new-secret-password"},
                )
                assert new_login.status_code == 200
                assert new_login.json()["authenticated"] is True
                assert new_login.json()["username"] == "trungadmin"
