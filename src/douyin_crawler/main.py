from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.database import create_database_engine
from douyin_crawler.crawler import (
    CrawlRunner,
    DouyinContentAdapter,
    HttpxMediaAdapter,
    MediaHttpAdapter,
    PlaywrightDouyinContentAdapter,
)
from douyin_crawler.browser import (
    BrowserSessionManager,
    BrowserSessionStatus,
    DouyinBrowserAdapter,
    PlaywrightDouyinBrowserAdapter,
)
from douyin_crawler.settings import get_settings
from douyin_crawler.targets import TargetService, create_targets_router
from douyin_crawler.videos import create_videos_router
from douyin_crawler.downloads import DownloadRunner, create_downloads_router
from douyin_crawler.logs import create_logs_router


class BrowserStatusResponse(BaseModel):
    status: BrowserSessionStatus


def create_app(
    *,
    database_url: str | None = None,
    browser_adapter: DouyinBrowserAdapter | None = None,
    browser_profile_directory: Path | None = None,
    content_adapter: DouyinContentAdapter | None = None,
    media_adapter: MediaHttpAdapter | None = None,
    covers_directory: Path | None = None,
    downloads_directory: Path | None = None,
    start_scheduler: bool = True,
    load_schedules: bool = True,
) -> FastAPI:
    scheduler = AsyncIOScheduler()
    engine = create_database_engine(database_url)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    browser_session = BrowserSessionManager(
        browser_adapter or PlaywrightDouyinBrowserAdapter(),
        browser_profile_directory or get_settings().browser_profile_directory,
    )
    crawl_runner = CrawlRunner(
        sessions,
        browser_session,
        content_adapter or PlaywrightDouyinContentAdapter(),
        media_adapter or HttpxMediaAdapter(),
        covers_directory or get_settings().covers_directory,
    )
    target_service = TargetService(sessions, scheduler, crawl_runner.start)
    download_runner = DownloadRunner(
        sessions, browser_session, content_adapter or PlaywrightDouyinContentAdapter(),
        media_adapter or HttpxMediaAdapter(),
        downloads_directory or get_settings().downloads_directory,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if start_scheduler:
            scheduler.start()
        app.state.scheduler = scheduler
        app.state.database_engine = engine
        app.state.browser_session = browser_session
        app.state.target_service = target_service
        app.state.crawl_runner = crawl_runner
        app.state.download_runner = download_runner
        if load_schedules:
            await target_service.synchronize_schedules()
        yield
        await browser_session.close()
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await engine.dispose()

    app = FastAPI(title="Douyin Crawler", lifespan=lifespan)
    app.include_router(create_targets_router(target_service))
    app.include_router(create_videos_router(sessions))
    app.include_router(create_downloads_router(download_runner))
    app.include_router(create_logs_router(sessions))

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "scheduler": "running" if scheduler.running else "stopped",
        }

    @app.get("/api/browser/status")
    async def browser_status() -> BrowserStatusResponse:
        status = await browser_session.get_status()
        return BrowserStatusResponse(status=status)

    @app.post("/api/browser/login", status_code=202)
    async def browser_login() -> BrowserStatusResponse:
        status = browser_session.start_login()
        return BrowserStatusResponse(status=status)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        template = Path(__file__).parent / "templates" / "dashboard.html"
        return HTMLResponse(template.read_text(encoding="utf-8"))

    return app


app = create_app()
