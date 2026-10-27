from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.anti_bot import create_anti_bot_router
from douyin_crawler.browser import (
    BrowserSessionManager,
    BrowserSessionStatus,
    DouyinBrowserAdapter,
    PlaywrightDouyinBrowserAdapter,
)
from douyin_crawler.crawler import (
    CrawlRunner,
    DouyinContentAdapter,
    HttpxMediaAdapter,
    MediaHttpAdapter,
    PlaywrightDouyinContentAdapter,
    create_crawl_router,
)
from douyin_crawler.database import create_database_engine
from douyin_crawler.downloads import DownloadRunner, create_downloads_router
from douyin_crawler.logs import create_logs_router
from douyin_crawler.models import CrawlLog, CrawlTarget, DouyinVideo
from douyin_crawler.settings import get_settings
from douyin_crawler.targets import TargetService, create_targets_router
from douyin_crawler.videos import create_bookmarks_router, create_videos_router


class BrowserStatusResponse(BaseModel):
    status: BrowserSessionStatus


class SchedulerStatusResponse(BaseModel):
    running: bool
    paused: bool
    jobs_count: int


class OverviewStatsResponse(BaseModel):
    total_videos: int
    downloaded_videos: int
    bookmarked_videos: int
    active_targets: int
    total_targets: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int


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
    download_runner = DownloadRunner(
        sessions,
        browser_session,
        content_adapter or PlaywrightDouyinContentAdapter(),
        media_adapter or HttpxMediaAdapter(),
        downloads_directory or get_settings().downloads_directory,
    )
    crawl_runner = CrawlRunner(
        sessions,
        browser_session,
        content_adapter or PlaywrightDouyinContentAdapter(),
        media_adapter or HttpxMediaAdapter(),
        covers_directory or get_settings().covers_directory,
        download_callback=download_runner.start,
    )
    target_service = TargetService(sessions, scheduler, crawl_runner.start)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if start_scheduler:
            scheduler.start()
        app.state.scheduler = scheduler
        app.state.scheduler_paused = False
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
    app.include_router(create_crawl_router(sessions, crawl_runner, scheduler))
    app.include_router(create_videos_router(sessions))
    app.include_router(create_bookmarks_router(sessions, target_service))
    app.include_router(create_downloads_router(download_runner))
    app.include_router(create_logs_router(sessions, crawl_runner))
    app.include_router(create_anti_bot_router(sessions))

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "scheduler": "running" if scheduler.running else "stopped",
        }

    @app.get("/api/stats")
    async def overview_stats() -> OverviewStatsResponse:
        async with sessions() as session:
            total_videos = await session.scalar(select(func.count()).select_from(DouyinVideo)) or 0
            downloaded_videos = (
                await session.scalar(
                    select(func.count())
                    .select_from(DouyinVideo)
                    .where(DouyinVideo.download_status == "COMPLETED")
                )
                or 0
            )
            bookmarked_videos = (
                await session.scalar(
                    select(func.count())
                    .select_from(DouyinVideo)
                    .where(DouyinVideo.is_bookmarked.is_(True))
                )
                or 0
            )
            total_targets = await session.scalar(select(func.count()).select_from(CrawlTarget)) or 0
            active_targets = (
                await session.scalar(
                    select(func.count())
                    .select_from(CrawlTarget)
                    .where(CrawlTarget.is_active.is_(True))
                )
                or 0
            )
            running_jobs = (
                await session.scalar(
                    select(func.count())
                    .select_from(CrawlLog)
                    .where(CrawlLog.status == "RUNNING")
                )
                or 0
            )
            completed_jobs = (
                await session.scalar(
                    select(func.count())
                    .select_from(CrawlLog)
                    .where(CrawlLog.status == "SUCCESS")
                )
                or 0
            )
            failed_jobs = (
                await session.scalar(
                    select(func.count())
                    .select_from(CrawlLog)
                    .where(CrawlLog.status.in_(["FAILED", "CAPTCHA_BLOCKED"]))
                )
                or 0
            )
        return OverviewStatsResponse(
            total_videos=total_videos,
            downloaded_videos=downloaded_videos,
            bookmarked_videos=bookmarked_videos,
            active_targets=active_targets,
            total_targets=total_targets,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
        )

    @app.get("/api/browser/status")
    async def browser_status() -> BrowserStatusResponse:
        status = await browser_session.get_status()
        return BrowserStatusResponse(status=status)

    @app.post("/api/browser/login", status_code=202)
    async def browser_login() -> BrowserStatusResponse:
        status = browser_session.start_login()
        return BrowserStatusResponse(status=status)

    @app.get("/api/scheduler/status")
    async def scheduler_status() -> SchedulerStatusResponse:
        return SchedulerStatusResponse(
            running=bool(scheduler.running),
            paused=bool(getattr(app.state, "scheduler_paused", False)),
            jobs_count=len(scheduler.get_jobs()),
        )

    @app.post("/api/scheduler/pause")
    async def pause_scheduler() -> SchedulerStatusResponse:
        if scheduler.running:
            scheduler.pause()
        app.state.scheduler_paused = True
        return SchedulerStatusResponse(
            running=bool(scheduler.running),
            paused=True,
            jobs_count=len(scheduler.get_jobs()),
        )

    @app.post("/api/scheduler/resume")
    async def resume_scheduler() -> SchedulerStatusResponse:
        if scheduler.running:
            scheduler.resume()
        app.state.scheduler_paused = False
        return SchedulerStatusResponse(
            running=bool(scheduler.running),
            paused=False,
            jobs_count=len(scheduler.get_jobs()),
        )

    frontend_dist = Path(__file__).parents[2] / "frontend" / "dist"
    if (frontend_dist / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(frontend_dist / "assets")),
            name="frontend_assets",
        )

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        dist_index = frontend_dist / "index.html"
        if dist_index.is_file():
            return HTMLResponse(dist_index.read_text(encoding="utf-8"))
        template = Path(__file__).parent / "templates" / "dashboard.html"
        return HTMLResponse(template.read_text(encoding="utf-8"))

    return app


app = create_app()
