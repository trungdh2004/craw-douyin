from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.models import CrawlTarget


class TargetType(StrEnum):
    CHANNEL = "CHANNEL"
    KEYWORD = "KEYWORD"
    COLLECT = "COLLECT"


class ScheduleType(StrEnum):
    INTERVAL = "INTERVAL"
    DAILY = "DAILY"
    ONCE = "ONCE"
    CRON = "CRON"
    MANUAL = "MANUAL"


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_type: TargetType
    target_value: str = Field(min_length=1)
    cron_expr: str = "0 */6 * * *"
    schedule_type: ScheduleType = ScheduleType.CRON
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    run_at: datetime | None = None
    auto_download: bool = False
    max_items_per_run: int = Field(default=50, gt=0)
    is_active: bool = True

    @field_validator("cron_expr")
    @classmethod
    def valid_cron(cls, value: str) -> str:
        CronTrigger.from_crontab(value)
        return value


class TargetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    target_value: str | None = Field(default=None, min_length=1)
    cron_expr: str | None = None
    schedule_type: ScheduleType | None = None
    schedule_config: dict[str, Any] | None = None
    run_at: datetime | None = None
    auto_download: bool | None = None
    max_items_per_run: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("cron_expr")
    @classmethod
    def valid_cron(cls, value: str | None) -> str | None:
        if value is not None:
            CronTrigger.from_crontab(value)
        return value


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_type: TargetType
    target_value: str
    cron_expr: str
    schedule_type: ScheduleType
    schedule_config: dict[str, Any]
    run_at: datetime | None
    auto_download: bool
    max_items_per_run: int
    is_active: bool
    last_status: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    scheduled: bool


class TargetService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        scheduler: AsyncIOScheduler,
        run_target: Callable[[int], object],
    ) -> None:
        self._sessions = sessions
        self._scheduler = scheduler
        self._run_target = run_target

    async def synchronize_schedules(self) -> None:
        async with self._sessions() as session:
            targets = list(
                await session.scalars(
                    select(CrawlTarget).where(CrawlTarget.is_active.is_(True))
                )
            )
        for target in targets:
            self._schedule(target)

    async def list(self) -> list[TargetResponse]:
        async with self._sessions() as session:
            targets = list(
                await session.scalars(select(CrawlTarget).order_by(CrawlTarget.id))
            )
            return [self._response(target) for target in targets]

    async def create(self, payload: TargetCreate) -> TargetResponse:
        async with self._sessions() as session:
            data = payload.model_dump()
            data["target_type"] = payload.target_type.value
            data["schedule_type"] = payload.schedule_type.value
            target = CrawlTarget(**data)
            session.add(target)
            await session.commit()
            await session.refresh(target)
            self._sync_schedule(target)
            return self._response(target)

    async def update(self, target_id: int, payload: TargetUpdate) -> TargetResponse:
        async with self._sessions() as session:
            target = await session.get(CrawlTarget, target_id)
            if target is None:
                raise HTTPException(status_code=404, detail="Crawl target not found")
            for field, value in payload.model_dump(exclude_unset=True).items():
                if isinstance(value, StrEnum):
                    value = value.value
                setattr(target, field, value)
            await session.commit()
            await session.refresh(target)
            self._sync_schedule(target)
            return self._response(target)

    async def delete(self, target_id: int) -> None:
        async with self._sessions() as session:
            target = await session.get(CrawlTarget, target_id)
            if target is None:
                raise HTTPException(status_code=404, detail="Crawl target not found")
            await session.delete(target)
            await session.commit()
        self._remove_schedule(target_id)

    async def run_now(self, target_id: int) -> None:
        async with self._sessions() as session:
            if await session.get(CrawlTarget, target_id) is None:
                raise HTTPException(status_code=404, detail="Crawl target not found")
        self._run_target(target_id)

    def _sync_schedule(self, target: CrawlTarget) -> None:
        if target.is_active:
            self._schedule(target)
        else:
            self._remove_schedule(target.id)

    def _schedule(self, target: CrawlTarget) -> None:
        trigger = self._build_trigger(target)
        if trigger is None:
            self._remove_schedule(target.id)
            return
        trigger_type = "ONCE" if target.schedule_type == ScheduleType.ONCE.value else "SCHEDULED"
        self._scheduler.add_job(
            self._run_target,
            trigger,
            args=[target.id],
            kwargs={"trigger_type": trigger_type},
            id=self._job_id(target.id),
            replace_existing=True,
        )

    @staticmethod
    def _build_trigger(target: CrawlTarget) -> BaseTrigger | None:
        schedule_type = target.schedule_type or "CRON"
        config = target.schedule_config or {}
        if schedule_type == ScheduleType.MANUAL.value:
            return None
        if schedule_type == ScheduleType.INTERVAL.value:
            every = max(1, int(config.get("every", 60)))
            unit = str(config.get("unit", "minutes")).lower()
            if unit == "hours":
                return IntervalTrigger(hours=every)
            return IntervalTrigger(minutes=every)
        if schedule_type == ScheduleType.DAILY.value:
            hour = int(config.get("hour", 8))
            minute = int(config.get("minute", 0))
            days_of_week = str(config.get("days_of_week") or "*")
            return CronTrigger(hour=hour, minute=minute, day_of_week=days_of_week)
        if schedule_type == ScheduleType.ONCE.value:
            if target.run_at is None:
                return None
            return DateTrigger(run_date=target.run_at)
        return CronTrigger.from_crontab(target.cron_expr)

    def _remove_schedule(self, target_id: int) -> None:
        job = self._scheduler.get_job(self._job_id(target_id))
        if job is not None:
            self._scheduler.remove_job(job.id)

    def _response(self, target: CrawlTarget) -> TargetResponse:
        job = self._scheduler.get_job(self._job_id(target.id))
        next_run_at: datetime | None = None
        if job is not None:
            next_run_at = getattr(job, "next_run_time", None)
            if next_run_at is None and hasattr(job, "trigger"):
                next_run_at = job.trigger.get_next_fire_time(None, datetime.now(UTC))
        return TargetResponse.model_validate(
            {
                **{
                    field: getattr(target, field)
                    for field in TargetResponse.model_fields
                    if field not in ("scheduled", "next_run_at")
                },
                "next_run_at": next_run_at,
                "scheduled": job is not None,
            }
        )

    @staticmethod
    def _job_id(target_id: int) -> str:
        return f"crawl-target-{target_id}"


def create_targets_router(service: TargetService) -> APIRouter:
    router = APIRouter(prefix="/api/targets", tags=["targets"])

    @router.get("")
    async def list_targets() -> list[TargetResponse]:
        return await service.list()

    @router.post("", status_code=201)
    async def create_target(payload: TargetCreate) -> TargetResponse:
        return await service.create(payload)

    @router.put("/{target_id}")
    async def update_target(target_id: int, payload: TargetUpdate) -> TargetResponse:
        return await service.update(target_id, payload)

    @router.delete("/{target_id}", status_code=204)
    async def delete_target(target_id: int) -> Response:
        await service.delete(target_id)
        return Response(status_code=204)

    @router.post("/{target_id}/run", status_code=202)
    async def run_target(target_id: int) -> dict[str, str]:
        await service.run_now(target_id)
        return {"status": "ACCEPTED"}

    return router
