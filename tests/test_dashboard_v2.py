import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.crawler import ScrapedPost
from douyin_crawler.main import create_app
from douyin_crawler.models import CrawlTarget


class AuthenticatedBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return BrowserSessionStatus.AUTHENTICATED

    async def open_login(self, profile_directory: Path) -> None:
        return None


class OverviewContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        yield [
            ScrapedPost(
                aweme_id="vid-overview-1",
                aweme_type=0,
                description="Bài tổng quan 1",
                hashtags=["overview"],
                create_time=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                author_sec_uid="sec-1",
                author_nickname="Kênh 1",
                author_avatar="https://avatar/1",
                digg_count=100,
                comment_count=10,
                share_count=5,
                collect_count=20,
                cover_url="https://cover/1",
                video_url="https://video/1",
                image_urls=[],
                is_top=False,
            )
        ]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


class OkMediaAdapter:
    async def fetch(self, url: str) -> tuple[int, bytes]:
        return 200, b"media-bytes"


async def test_operator_can_view_dashboard_overview_stats(tmp_path: Path) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=OverviewContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                initial_stats = await client.get("/api/stats")
                created = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh tổng quan",
                        "target_type": "CHANNEL",
                        "target_value": "sec-1",
                        "cron_expr": "0 */6 * * *",
                        "max_items_per_run": 10,
                    },
                )
                target_id = created.json()["id"]
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()
                await client.post("/api/videos/vid-overview-1/download")
                await app.state.download_runner.wait()
                updated_stats = await client.get("/api/stats")

    assert initial_stats.status_code == 200
    assert initial_stats.json() == {
        "total_videos": 0,
        "downloaded_videos": 0,
        "bookmarked_videos": 0,
        "active_targets": 0,
        "total_targets": 0,
        "running_jobs": 0,
        "completed_jobs": 0,
        "failed_jobs": 0,
    }
    assert updated_stats.status_code == 200
    assert updated_stats.json()["total_videos"] == 1
    assert updated_stats.json()["downloaded_videos"] == 1
    assert updated_stats.json()["active_targets"] == 1
    assert updated_stats.json()["total_targets"] == 1
    assert updated_stats.json()["completed_jobs"] >= 1


class RichMetadataContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        yield [
            ScrapedPost(
                aweme_id="vid-short",
                aweme_type=0,
                description="Video ngắn 15s",
                hashtags=["short", "viral"],
                create_time=datetime(2026, 10, 21, 8, 30, tzinfo=UTC),
                author_sec_uid="sec-author-1",
                author_nickname="Creator A",
                author_avatar="https://avatar/a",
                digg_count=500,
                comment_count=40,
                share_count=12,
                collect_count=88,
                cover_url="https://cover/short",
                video_url="https://video/short",
                image_urls=[],
                is_top=False,
                duration_ms=15000,
                width=1080,
                height=1920,
                music_title="Nhạc nền xu hướng",
                music_author="DJ Douyin",
            ),
            ScrapedPost(
                aweme_id="vid-long",
                aweme_type=0,
                description="Video dài 95s",
                hashtags=["longform"],
                create_time=datetime(2026, 10, 22, 10, 0, tzinfo=UTC),
                author_sec_uid="sec-author-2",
                author_nickname="Creator B",
                author_avatar="https://avatar/b",
                digg_count=1200,
                comment_count=90,
                share_count=35,
                collect_count=210,
                cover_url="https://cover/long",
                video_url="https://video/long",
                image_urls=[],
                is_top=False,
                duration_ms=95000,
                width=1920,
                height=1080,
                music_title="Original Sound",
                music_author="Creator B",
            ),
        ]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


async def test_library_exposes_video_duration_rich_metadata_and_local_media_stream(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=RichMetadataContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                created = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh Metadata",
                        "target_type": "CHANNEL",
                        "target_value": "sec-author-1",
                        "cron_expr": "0 */6 * * *",
                        "max_items_per_run": 10,
                    },
                )
                target_id = created.json()["id"]
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()

                long_only = await client.get(
                    "/api/videos",
                    params={"min_duration_ms": 60000, "sort": "duration_ms", "order": "desc"},
                )
                await client.post("/api/videos/vid-long/download")
                await app.state.download_runner.wait()
                stream_response = await client.get("/api/videos/vid-long/stream")

    assert long_only.status_code == 200
    data = long_only.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["aweme_id"] == "vid-long"
    assert item["duration_ms"] == 95000
    assert item["width"] == 1920
    assert item["height"] == 1080
    assert item["music_title"] == "Original Sound"
    assert item["music_author"] == "Creator B"
    assert item["author_sec_uid"] == "sec-author-2"
    assert item["crawled_at"] is not None
    assert stream_response.status_code == 200
    assert stream_response.content == b"media-bytes"


class BookmarkAndCollectContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        if target.target_type == "COLLECT":
            yield [
                ScrapedPost(
                    aweme_id="collect-1",
                    aweme_type=0,
                    description="Bài đã lưu trên Douyin",
                    hashtags=["saved"],
                    create_time=datetime(2026, 10, 23, 9, 0, tzinfo=UTC),
                    author_sec_uid="sec-saved",
                    author_nickname="Saved Creator",
                    author_avatar=None,
                    digg_count=800,
                    comment_count=50,
                    share_count=20,
                    collect_count=300,
                    cover_url="https://cover/collect-1",
                    video_url="https://video/collect-1",
                    image_urls=[],
                    duration_ms=42000,
                )
            ]
        else:
            yield [
                ScrapedPost(
                    aweme_id="regular-1",
                    aweme_type=0,
                    description="Bài kênh thường 1",
                    hashtags=["regular"],
                    create_time=datetime(2026, 10, 23, 8, 0, tzinfo=UTC),
                    author_sec_uid="sec-reg",
                    author_nickname="Regular Creator",
                    author_avatar=None,
                    digg_count=100,
                    comment_count=10,
                    share_count=5,
                    collect_count=15,
                    cover_url="https://cover/regular-1",
                    video_url="https://video/regular-1",
                    image_urls=[],
                    duration_ms=20000,
                ),
                ScrapedPost(
                    aweme_id="regular-2",
                    aweme_type=0,
                    description="Bài kênh thường 2",
                    hashtags=["regular"],
                    create_time=datetime(2026, 10, 23, 8, 5, tzinfo=UTC),
                    author_sec_uid="sec-reg",
                    author_nickname="Regular Creator",
                    author_avatar=None,
                    digg_count=200,
                    comment_count=20,
                    share_count=10,
                    collect_count=30,
                    cover_url="https://cover/regular-2",
                    video_url="https://video/regular-2",
                    image_urls=[],
                    duration_ms=30000,
                ),
            ]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


async def test_operator_can_bookmark_posts_and_sync_douyin_collect(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=BookmarkAndCollectContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                ch = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh Thường",
                        "target_type": "CHANNEL",
                        "target_value": "sec-reg",
                    },
                )
                await client.post(f"/api/targets/{ch.json()['id']}/run")
                await app.state.crawl_runner.wait()

                patched = await client.patch(
                    "/api/videos/regular-1/bookmark",
                    json={
                        "is_bookmarked": True,
                        "bookmark_collection": "Idea kịch bản",
                        "bookmark_note": "Mở đầu rất cuốn",
                    },
                )
                batch_bm = await client.post(
                    "/api/videos/batch-bookmark",
                    json={
                        "aweme_ids": ["regular-2"],
                        "is_bookmarked": True,
                        "bookmark_collection": "Nhạc hay",
                    },
                )
                sync_res = await client.post("/api/bookmarks/sync-douyin")
                await app.state.crawl_runner.wait()

                bookmarked_list = await client.get(
                    "/api/videos", params={"is_bookmarked": True}
                )
                idea_list = await client.get(
                    "/api/videos",
                    params={"is_bookmarked": True, "bookmark_collection": "Idea kịch bản"},
                )
                collections_res = await client.get("/api/bookmarks/collections")

    assert patched.status_code == 200
    assert patched.json()["is_bookmarked"] is True
    assert patched.json()["bookmark_collection"] == "Idea kịch bản"
    assert patched.json()["bookmark_note"] == "Mở đầu rất cuốn"
    assert batch_bm.status_code == 200
    assert sync_res.status_code == 202
    assert bookmarked_list.json()["total"] == 3
    assert idea_list.json()["total"] == 1
    assert idea_list.json()["items"][0]["aweme_id"] == "regular-1"
    collections = {c["name"]: c["count"] for c in collections_res.json()}
    assert collections["Idea kịch bản"] == 1
    assert collections["Nhạc hay"] == 1


class SingleItemContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        if False:
            yield []

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        resolved_id = "7399999999999999999" if "v.douyin.com" in aweme_id else aweme_id
        return ScrapedPost(
            aweme_id=resolved_id,
            aweme_type=0,
            description=f"Bài lẻ {resolved_id}",
            hashtags=["single"],
            create_time=datetime(2026, 10, 24, 15, 0, tzinfo=UTC),
            author_sec_uid="sec-single",
            author_nickname="Single Creator",
            author_avatar=None,
            digg_count=999,
            comment_count=88,
            share_count=77,
            collect_count=66,
            cover_url=f"https://cover/{resolved_id}",
            video_url=f"https://video/{resolved_id}",
            image_urls=[],
            duration_ms=28000,
        )


async def test_operator_can_crawl_single_ids_links_and_schedule_one_off_crawl(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=SingleItemContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                immediate = await client.post(
                    "/api/crawl/items",
                    json={
                        "inputs": [
                            "7311111111111111111",
                            "https://www.douyin.com/video/7322222222222222222?modeFrom=userPost",
                            "4.89 复制打开抖音，看看作品 https://v.douyin.com/iYAbCdE/ 03/15",
                        ],
                        "auto_download": True,
                        "is_bookmarked": True,
                        "bookmark_collection": "Crawl lẻ",
                    },
                )
                await app.state.crawl_runner.wait()
                await app.state.download_runner.wait()

                future_time = "2026-12-31T23:59:00Z"
                scheduled = await client.post(
                    "/api/crawl/items",
                    json={
                        "inputs": ["7388888888888888888"],
                        "auto_download": False,
                        "is_bookmarked": False,
                        "run_at": future_time,
                    },
                )

                videos_res = await client.get("/api/videos")
                logs_res = await client.get("/api/logs", params={"job_type": "SINGLE_CRAWL"})

    assert immediate.status_code == 202
    immediate_ids = {item["aweme_id"] for item in videos_res.json()["items"]}
    assert immediate_ids == {
        "7311111111111111111",
        "7322222222222222222",
        "7399999999999999999",
    }
    for item in videos_res.json()["items"]:
        assert item["download_status"] == "COMPLETED"
        assert item["is_bookmarked"] is True
        assert item["bookmark_collection"] == "Crawl lẻ"
    assert scheduled.status_code == 202
    assert scheduled.json()["status"] == "SCHEDULED"
    assert logs_res.json()["total"] == 2


async def test_operator_can_configure_visual_schedules_auto_download_and_pause_scheduler(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=OverviewContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=True,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                interval_target = await client.post(
                    "/api/targets",
                    json={
                        "name": "Quét mỗi 45 phút",
                        "target_type": "CHANNEL",
                        "target_value": "sec-interval",
                        "schedule_type": "INTERVAL",
                        "schedule_config": {"every": 45, "unit": "minutes"},
                        "auto_download": True,
                    },
                )
                daily_target = await client.post(
                    "/api/targets",
                    json={
                        "name": "Quét 8h30 sáng",
                        "target_type": "KEYWORD",
                        "target_value": "xu hướng",
                        "schedule_type": "DAILY",
                        "schedule_config": {"hour": 8, "minute": 30, "days_of_week": "mon,wed,fri"},
                    },
                )
                once_target = await client.post(
                    "/api/targets",
                    json={
                        "name": "Chạy 1 lần",
                        "target_type": "CHANNEL",
                        "target_value": "sec-once",
                        "schedule_type": "ONCE",
                        "run_at": "2026-12-31T10:00:00Z",
                    },
                )

                target_id = interval_target.json()["id"]
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()
                await app.state.download_runner.wait()

                once_id = once_target.json()["id"]
                await client.post(f"/api/targets/{once_id}/run")
                await app.state.crawl_runner.wait()
                targets_after_once = await client.get("/api/targets")

                videos_after_auto = await client.get("/api/videos")
                paused_res = await client.post("/api/scheduler/pause")
                resumed_res = await client.post("/api/scheduler/resume")

    assert interval_target.status_code == 201
    assert interval_target.json()["schedule_type"] == "INTERVAL"
    assert interval_target.json()["auto_download"] is True
    assert interval_target.json()["next_run_at"] is not None
    assert daily_target.status_code == 201
    assert daily_target.json()["schedule_type"] == "DAILY"
    assert daily_target.json()["next_run_at"] is not None
    assert once_target.status_code == 201
    assert once_target.json()["schedule_type"] == "ONCE"
    assert once_target.json()["next_run_at"] is not None
    once_after = next(t for t in targets_after_once.json() if t["id"] == once_id)
    assert once_after["is_active"] is False
    assert videos_after_auto.json()["items"][0]["download_status"] == "COMPLETED"
    assert paused_res.status_code == 200
    assert paused_res.json()["paused"] is True
    assert resumed_res.status_code == 200
    assert resumed_res.json()["paused"] is False


class CaptchaTriggeringContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        from douyin_crawler.crawler import CaptchaDetectedError

        yield [
            ScrapedPost(
                aweme_id="before-captcha-1",
                aweme_type=0,
                description="Bài trước khi dính Captcha",
                hashtags=[],
                create_time=datetime(2026, 10, 25, 10, 0, tzinfo=UTC),
                author_sec_uid="sec-cap",
                author_nickname="Creator Captcha",
                author_avatar=None,
                digg_count=10,
                comment_count=1,
                share_count=1,
                collect_count=1,
                cover_url="https://cover/cap1",
                video_url="https://video/cap1",
                image_urls=[],
                duration_ms=12000,
            )
        ]
        raise CaptchaDetectedError("Douyin yêu cầu kéo hình xác thực Captcha")

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


async def test_operator_can_configure_anti_bot_presets_and_handle_captcha_block(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=CaptchaTriggeringContentAdapter(),
            media_adapter=OkMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                default_settings = await client.get("/api/settings/anti-bot")
                safe_settings = await client.put(
                    "/api/settings/anti-bot",
                    json={"preset": "SAFE", "proxy_url": "http://127.0.0.1:7890"},
                )
                created = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh Captcha",
                        "target_type": "CHANNEL",
                        "target_value": "sec-cap",
                    },
                )
                target_id = created.json()["id"]
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()

                browser_after_captcha = await client.get("/api/browser/status")
                logs_after_captcha = await client.get("/api/logs")

    assert default_settings.status_code == 200
    assert default_settings.json()["preset"] == "BALANCED"
    assert safe_settings.status_code == 200
    assert safe_settings.json()["preset"] == "SAFE"
    assert safe_settings.json()["scroll_delay_min_ms"] == 3000
    assert safe_settings.json()["proxy_url"] == "http://127.0.0.1:7890"
    assert browser_after_captcha.json()["status"] == "CAPTCHA_REQUIRED"
    assert logs_after_captcha.json()["items"][0]["status"] == "CAPTCHA_BLOCKED"


class FlakyThenSuccessAdapter:
    def __init__(self) -> None:
        self.attempts = 0

    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("Lỗi mạng tạm thời")
        yield [
            ScrapedPost(
                aweme_id="retry-ok-1",
                aweme_type=0,
                description="Thành công sau khi retry",
                hashtags=[],
                create_time=datetime(2026, 10, 26, 12, 0, tzinfo=UTC),
                author_sec_uid="sec-retry",
                author_nickname="Retry Creator",
                author_avatar=None,
                digg_count=50,
                comment_count=5,
                share_count=2,
                collect_count=8,
                cover_url="https://cover/retry1",
                video_url="https://video/retry1",
                image_urls=[],
                duration_ms=18000,
            )
        ]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


class FlakyMediaAdapter:
    def __init__(self) -> None:
        self.video_attempts = 0

    async def fetch(self, url: str) -> tuple[int, bytes]:
        if url.startswith("https://video/"):
            self.video_attempts += 1
            if self.video_attempts == 1:
                return 500, b""
        return 200, b"media-bytes"


async def test_operator_can_filter_retry_and_clear_execution_history(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=AuthenticatedBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=FlakyThenSuccessAdapter(),
            media_adapter=FlakyMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
        )

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                created = await client.post(
                    "/api/targets",
                    json={
                        "name": "Kênh Hay Lỗi",
                        "target_type": "CHANNEL",
                        "target_value": "sec-retry",
                    },
                )
                target_id = created.json()["id"]
                await client.post(f"/api/targets/{target_id}/run")
                await app.state.crawl_runner.wait()

                failed_logs = await client.get("/api/logs", params={"status": "FAILED"})
                failed_log_id = failed_logs.json()["items"][0]["id"]

                retried = await client.post(f"/api/logs/{failed_log_id}/retry")
                await app.state.crawl_runner.wait()

                # Trigger a download that fails on 1st attempt, then retry via /api/logs/{id}/retry
                await client.post("/api/videos/retry-ok-1/download")
                await app.state.download_runner.wait()
                dl_failed_logs = await client.get(
                    "/api/logs", params={"job_type": "DOWNLOAD", "status": "FAILED"}
                )
                dl_failed_id = dl_failed_logs.json()["items"][0]["id"]
                dl_retried = await client.post(f"/api/logs/{dl_failed_id}/retry")
                await app.state.download_runner.wait()
                dl_success_logs = await client.get(
                    "/api/logs", params={"job_type": "DOWNLOAD", "status": "SUCCESS"}
                )

                all_logs = await client.get("/api/logs")
                deleted_single = await client.delete(f"/api/logs/{failed_log_id}")
                cleared = await client.delete("/api/logs")
                empty_logs = await client.get("/api/logs")

    assert failed_logs.json()["total"] == 1
    assert failed_logs.json()["items"][0]["duration_ms"] is not None
    assert retried.status_code == 202
    assert dl_failed_logs.json()["total"] == 1
    assert dl_retried.status_code == 202
    assert dl_success_logs.json()["total"] == 1
    assert dl_success_logs.json()["items"][0]["trigger_type"] == "RETRY"
    assert all_logs.json()["total"] == 4
    assert deleted_single.status_code == 204
    assert cleared.status_code == 200
    assert empty_logs.json()["total"] == 0






