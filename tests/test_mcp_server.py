import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
import httpx
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from douyin_crawler.browser import BrowserSessionStatus
from douyin_crawler.crawler import ScrapedPost
from douyin_crawler.main import create_app
from douyin_crawler.mcp_server import DouyinMcpServer
from douyin_crawler.models import CrawlTarget


class StubBrowserAdapter:
    async def get_status(self, profile_directory: Path) -> BrowserSessionStatus:
        return BrowserSessionStatus.AUTHENTICATED

    async def open_login(self, profile_directory: Path) -> None:
        return None


class StubContentAdapter:
    async def crawl(
        self, profile: Path, target: CrawlTarget
    ) -> AsyncIterator[list[ScrapedPost]]:
        now = datetime(2026, 10, 28, 8, 0, tzinfo=UTC)
        yield [
            ScrapedPost(
                aweme_id="vid-low-hearts",
                aweme_type=0,
                description="Video ít tim",
                hashtags=["ootd"],
                create_time=now,
                author_sec_uid="sec-1",
                author_nickname="Creator A",
                author_avatar=None,
                digg_count=500,
                comment_count=10,
                share_count=5,
                collect_count=20,
                duration_ms=15000,
                cover_url="https://example.com/c1.jpg",
                video_url="https://example.com/v1.mp4",
                image_urls=[],
                is_top=False,
            ),
            ScrapedPost(
                aweme_id="vid-top-1",
                aweme_type=0,
                description="Video nhiều tim số 1",
                hashtags=["ootd"],
                create_time=now,
                author_sec_uid="sec-1",
                author_nickname="Creator A",
                author_avatar=None,
                digg_count=95000,
                comment_count=1200,
                share_count=800,
                collect_count=4500,
                duration_ms=30000,
                cover_url="https://example.com/c2.jpg",
                video_url="https://example.com/v2.mp4",
                image_urls=[],
                is_top=False,
            ),
            ScrapedPost(
                aweme_id="vid-top-2",
                aweme_type=0,
                description="Video nhiều tim số 2",
                hashtags=["ootd"],
                create_time=now,
                author_sec_uid="sec-1",
                author_nickname="Creator B",
                author_avatar=None,
                digg_count=42000,
                comment_count=600,
                share_count=300,
                collect_count=1900,
                duration_ms=25000,
                cover_url="https://example.com/c3.jpg",
                video_url="https://example.com/v3.mp4",
                image_urls=[],
                is_top=False,
            ),
        ]

    async def detail(self, profile: Path, aweme_id: str) -> ScrapedPost:
        raise NotImplementedError


class StubMediaAdapter:
    async def fetch(self, url: str) -> tuple[int, bytes]:
        return 200, b"fake-mp4-bytes"


async def test_mcp_server_crawls_and_sends_top_hearted_videos_to_analysis(
    tmp_path: Path,
) -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        alembic_config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

        app = create_app(
            database_url=database_url,
            browser_adapter=StubBrowserAdapter(),
            browser_profile_directory=tmp_path / "profile",
            content_adapter=StubContentAdapter(),
            media_adapter=StubMediaAdapter(),
            covers_directory=tmp_path / "covers",
            downloads_directory=tmp_path / "downloads",
            start_scheduler=False,
            require_auth=True,
        )

        def mock_studio_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/lists":
                return httpx.Response(200, json={"items": []})
            if request.url.path == "/api/lists/import-crawler":
                payload = json.loads(request.content.decode("utf-8"))
                items = payload.get("items") or []
                return httpx.Response(
                    200,
                    json={
                        "id": "list-mcp-999",
                        "items": [
                            {"id": f"edit-item-{i+1}"} for i in range(len(items))
                        ],
                    },
                )
            return httpx.Response(404)

        async with app.router.lifespan_context(app):
            app.state.edit_bridge._http_client = httpx.AsyncClient(
                transport=httpx.MockTransport(mock_studio_handler)
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as http_client:
                mcp = DouyinMcpServer(
                    base_url="http://test",
                    username="admin",
                    password="admin123",
                    http_client=http_client,
                )

                # 1. Verify MCP initialize & tools/list
                init_res = await mcp.handle_rpc(
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
                )
                assert init_res is not None
                assert init_res["result"]["serverInfo"]["name"] == "douyin-crawler-mcp"

                tools_res = await mcp.handle_rpc(
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
                )
                assert tools_res is not None
                tool_names = {t["name"] for t in tools_res["result"]["tools"]}
                assert "crawl_and_send_top_videos" in tool_names
                assert "search_top_videos" in tool_names
                assert "trigger_crawl" in tool_names
                assert "send_videos_to_analysis" in tool_names
                assert "get_system_status" in tool_names
                assert "configure_analysis_server" in tool_names

                # 2. Configure analysis server IP & Port via MCP tool
                cfg_res = await mcp.call_tool(
                    "configure_analysis_server",
                    {"host": "192.168.1.88", "port": 9000},
                )
                assert cfg_res["base_url"] == "http://192.168.1.88:9000"

                # 3. Call one-shot crawl_and_send_top_videos (top_n=2)
                result: dict[str, Any] = await mcp.call_tool(
                    "crawl_and_send_top_videos",
                    {
                        "target_type": "KEYWORD",
                        "target_value": "穿搭",
                        "max_crawl_items": 20,
                        "top_n": 2,
                        "exclude_already_analyzed": True,
                    },
                )

                assert result["crawl_result"]["status"] == "SUCCESS"
                assert result["crawl_result"]["new_videos_count"] == 3

                selected = result["selected_videos"]
                assert [v["aweme_id"] for v in selected] == ["vid-top-1", "vid-top-2"]
                assert [v["digg_count"] for v in selected] == [95000, 42000]

                submission = result["analysis_submission"]
                assert submission["sent_count"] == 2
                assert submission["list_id"] == "list-mcp-999"
                assert "192.168.1.88:9000" in submission["studio_url"]

                # 4. Calling again with exclude_already_analyzed=True only picks the remaining unanalyzed video!
                second_result: dict[str, Any] = await mcp.call_tool(
                    "crawl_and_send_top_videos",
                    {
                        "target_type": "KEYWORD",
                        "target_value": "穿搭",
                        "max_crawl_items": 20,
                        "top_n": 2,
                        "exclude_already_analyzed": True,
                        "skip_crawl_if_existing": True,
                    },
                )
                selected_second = second_result["selected_videos"]
                assert [v["aweme_id"] for v in selected_second] == ["vid-low-hearts"]
                assert second_result["analysis_submission"]["sent_count"] == 1
