from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from douyin_crawler.database import create_database_engine


def create_app(
    *, database_url: str | None = None, start_scheduler: bool = True
) -> FastAPI:
    scheduler = AsyncIOScheduler()
    engine = create_database_engine(database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if start_scheduler:
            scheduler.start()
        app.state.scheduler = scheduler
        app.state.database_engine = engine
        yield
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await engine.dispose()

    app = FastAPI(title="Douyin Crawler", lifespan=lifespan)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "scheduler": "running" if scheduler.running else "stopped",
        }

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        template = Path(__file__).parent / "templates" / "dashboard.html"
        return HTMLResponse(template.read_text(encoding="utf-8"))

    return app


app = create_app()
