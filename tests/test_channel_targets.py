import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.main import create_app


class UnusedBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return BrowserSessionStatus.AUTHENTICATED

    async def open_login(self, profile_directory: Path) -> None:
        raise AssertionError("Login browser should not be opened")


async def test_operator_can_manage_scheduled_channel_target(tmp_path: Path) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")
        app = create_app(
            database_url=database_url,
            browser_adapter=UnusedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                created = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh demo",
                        "target_type": "CHANNEL",
                        "target_value": "MS4wLjABAAAA-demo",
                        "cron_expr": "*/15 * * * *",
                        "max_items_per_run": 20,
                    },
                )
                target_id = created.json()["id"]
                listed = await client.get("/api/targets")
                disabled = await client.put(
                    f"/api/targets/{target_id}", json={"is_active": False}
                )
                deleted = await client.delete(f"/api/targets/{target_id}")
                empty_list = await client.get("/api/targets")

    assert created.status_code == 201
    assert created.json()["scheduled"] is True
    assert listed.json()[0]["target_value"] == "MS4wLjABAAAA-demo"
    assert disabled.json()["is_active"] is False
    assert disabled.json()["scheduled"] is False
    assert deleted.status_code == 204
    assert empty_list.json() == []
