import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.crawler import ScrapedPost
from douyin_crawler.models import CrawlTarget
from douyin_crawler.main import create_app


class UnusedBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return BrowserSessionStatus.AUTHENTICATED

    async def open_login(self, profile_directory: Path) -> None:
        raise AssertionError("Login browser should not be opened")


class FakeContentAdapter:
    def __init__(self) -> None:
        self.calls = 0

    async def crawl(self, profile: Path, target: CrawlTarget) -> AsyncIterator[list[ScrapedPost]]:
        self.calls += 1
        ids = ["pin-1", "pin-2", "pin-3", "old-1", "old-2", "old-3"]
        if self.calls > 1:
            ids.append("must-not-be-read")
        yield [post(aweme_id, index < 3, self.calls) for index, aweme_id in enumerate(ids)]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        return post(aweme_id, False, self.calls)


class FakeMediaAdapter:
    def __init__(self) -> None:
        self.expired_once = False

    async def fetch(self, url: str) -> tuple[int, bytes]:
        if url.startswith("https://video/") and url.endswith("old-1") and not self.expired_once:
            self.expired_once = True
            return 403, b""
        return 200, b"cover"


def post(aweme_id: str, pinned: bool, run: int) -> ScrapedPost:
    return ScrapedPost(
        aweme_id=aweme_id, aweme_type=0, description=aweme_id, hashtags=["demo"],
        create_time=datetime(2026, 1, 1, tzinfo=UTC), author_sec_uid="author",
        author_nickname="Kênh demo", author_avatar=None, digg_count=run,
        comment_count=2, share_count=3, collect_count=4,
        cover_url=f"https://cover/{aweme_id}", video_url=f"https://video/{aweme_id}",
        image_urls=[], is_top=pinned,
    )


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
            content_adapter=FakeContentAdapter(),
            media_adapter=FakeMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
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
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()
                library = await client.get("/api/videos", params={"target_id": target_id, "min_digg": 2, "sort": "digg_count"})
                download = await client.post("/api/videos/old-1/download")
                await app.state.download_runner.wait()
                batch = await client.post("/api/videos/batch-download", json={"aweme_ids": ["old-2", "old-3"]})
                await app.state.download_runner.wait()
                logs = await client.get("/api/logs")
                connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
                stored_count = await connection.fetchval("SELECT count(*) FROM douyin_videos")
                unseen_count = await connection.fetchval("SELECT count(*) FROM douyin_videos WHERE aweme_id = 'must-not-be-read'")
                completed_logs = await connection.fetchval("SELECT count(*) FROM crawl_logs WHERE status = 'SUCCESS'")
                video_statuses = await connection.fetch("SELECT DISTINCT download_status FROM douyin_videos")
                completed_downloads = await connection.fetchval("SELECT count(*) FROM douyin_videos WHERE download_status = 'COMPLETED'")
                await connection.close()
                listed = await client.get("/api/targets")
                disabled = await client.put(
                    f"/api/targets/{target_id}", json={"is_active": False}
                )
                deleted = await client.delete(f"/api/targets/{target_id}")
                empty_list = await client.get("/api/targets")
                keyword = await client.post("/api/targets", json={"name": "Xu hướng", "target_type": "KEYWORD", "target_value": "ẩm thực", "cron_expr": "0 * * * *", "max_items_per_run": 2})

    assert created.status_code == 201
    assert created.json()["scheduled"] is True
    assert stored_count == 6
    assert unseen_count == 0
    assert completed_logs == 2
    assert {row["download_status"] for row in video_statuses} == {"NONE", "COMPLETED"}
    assert library.status_code == 200
    assert library.json()["total"] == 6
    assert download.status_code == 202
    assert batch.json()["accepted"] == 2
    assert completed_downloads == 3
    assert logs.json()["total"] == 2
    assert len(list((tmp_path / "covers").glob("*.jpg"))) == 6
    assert listed.json()[0]["target_value"] == "MS4wLjABAAAA-demo"
    assert disabled.json()["is_active"] is False
    assert disabled.json()["scheduled"] is False
    assert deleted.status_code == 204
    assert empty_list.json() == []
    assert keyword.status_code == 201
    assert keyword.json()["target_type"] == "KEYWORD"
