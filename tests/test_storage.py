from pathlib import Path
import asyncio

import asyncpg
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from douyin_crawler.main import create_app


async def test_migrations_persist_crawl_data_in_postgresql() -> None:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        database_url = postgres.get_connection_url()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.attributes["database_url"] = database_url
        await asyncio.to_thread(command.upgrade, config, "head")

        connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            target_id = await connection.fetchval(
                """
                INSERT INTO crawl_targets (name, target_type, target_value, cron_expr)
                VALUES ('Kênh thử nghiệm', 'CHANNEL', 'test-sec-uid', '0 */6 * * *')
                RETURNING id
                """
            )
            await connection.execute(
                """
                INSERT INTO douyin_videos (
                    aweme_id, target_id, aweme_type, description, create_time,
                    author_sec_uid, author_nickname
                ) VALUES ('7312345', $1, 0, 'Video thử nghiệm', NOW(), 'author-1', 'Tác giả')
                """,
                target_id,
            )
            await connection.execute(
                """
                INSERT INTO crawl_logs (target_id, status, new_videos_count)
                VALUES ($1, 'SUCCESS', 1)
                """,
                target_id,
            )

            stored = await connection.fetchrow(
                """
                SELECT t.name, v.description, v.download_status, l.new_videos_count
                FROM crawl_targets t
                JOIN douyin_videos v ON v.target_id = t.id
                JOIN crawl_logs l ON l.target_id = t.id
                WHERE v.aweme_id = '7312345'
                """
            )
        finally:
            await connection.close()

        app = create_app(database_url=database_url)
        async with app.router.lifespan_context(app):
            scheduler = app.state.scheduler
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                health_response = await client.get("/api/health")

        assert scheduler.running is False

    assert dict(stored) == {
        "name": "Kênh thử nghiệm",
        "description": "Video thử nghiệm",
        "download_status": "NONE",
        "new_videos_count": 1,
    }
    assert health_response.json() == {
        "status": "ok",
        "database": "connected",
        "scheduler": "running",
    }
