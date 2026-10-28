from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.models import AntiBotSettings

PresetName = Literal["SAFE", "BALANCED", "FAST", "CUSTOM"]

PRESET_DEFAULTS: dict[str, dict[str, int | bool]] = {
    "SAFE": {
        "scroll_delay_min_ms": 3000,
        "scroll_delay_max_ms": 6500,
        "download_delay_min_ms": 1200,
        "download_delay_max_ms": 3000,
        "cooldown_between_targets_sec": 25,
        "stealth_mode": True,
        "human_scroll": True,
        "auto_stop_on_captcha": True,
        "max_pages_per_run": 15,
    },
    "BALANCED": {
        "scroll_delay_min_ms": 1500,
        "scroll_delay_max_ms": 3500,
        "download_delay_min_ms": 500,
        "download_delay_max_ms": 1500,
        "cooldown_between_targets_sec": 10,
        "stealth_mode": True,
        "human_scroll": True,
        "auto_stop_on_captcha": True,
        "max_pages_per_run": 25,
    },
    "FAST": {
        "scroll_delay_min_ms": 600,
        "scroll_delay_max_ms": 1400,
        "download_delay_min_ms": 150,
        "download_delay_max_ms": 450,
        "cooldown_between_targets_sec": 3,
        "stealth_mode": True,
        "human_scroll": False,
        "auto_stop_on_captcha": True,
        "max_pages_per_run": 50,
    },
}


class AntiBotSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preset: PresetName
    scroll_delay_min_ms: int
    scroll_delay_max_ms: int
    download_delay_min_ms: int
    download_delay_max_ms: int
    cooldown_between_targets_sec: int
    stealth_mode: bool
    human_scroll: bool
    auto_stop_on_captcha: bool
    headless_mode: bool = False
    max_pages_per_run: int
    user_agent: str | None
    proxy_url: str | None
    edit_studio_host: str = "127.0.0.1"
    edit_studio_port: int = 8000
    updated_at: datetime


class AntiBotSettingsUpdate(BaseModel):
    preset: PresetName | None = None
    scroll_delay_min_ms: int | None = Field(default=None, ge=100, le=60000)
    scroll_delay_max_ms: int | None = Field(default=None, ge=100, le=60000)
    download_delay_min_ms: int | None = Field(default=None, ge=0, le=60000)
    download_delay_max_ms: int | None = Field(default=None, ge=0, le=60000)
    cooldown_between_targets_sec: int | None = Field(default=None, ge=0, le=3600)
    stealth_mode: bool | None = None
    human_scroll: bool | None = None
    auto_stop_on_captcha: bool | None = None
    headless_mode: bool | None = None
    max_pages_per_run: int | None = Field(default=None, ge=1, le=500)
    user_agent: str | None = None
    proxy_url: str | None = None
    edit_studio_host: str | None = None
    edit_studio_port: int | None = Field(default=None, ge=1, le=65535)


class EditStudioConfigResponse(BaseModel):
    host: str
    port: int
    base_url: str
    updated_at: datetime


class EditStudioConfigUpdate(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)


def format_edit_studio_base_url(host: str | None, port: int | None) -> str:
    clean_host = (host or "127.0.0.1").strip().rstrip("/")
    clean_port = int(port or 8000)
    if clean_host.startswith("http://") or clean_host.startswith("https://"):
        # Strip trailing port if user pasted full URL with port
        scheme, rest = clean_host.split("://", 1)
        host_only = rest.split("/")[0].split(":")[0]
        return f"{scheme}://{host_only}:{clean_port}"
    host_only = clean_host.split("/")[0].split(":")[0]
    return f"http://{host_only}:{clean_port}"


def normalize_host_input(raw_host: str) -> str:
    clean = raw_host.strip().rstrip("/")
    if clean.startswith("http://") or clean.startswith("https://"):
        _, rest = clean.split("://", 1)
        return rest.split("/")[0].split(":")[0] or "127.0.0.1"
    return clean.split("/")[0].split(":")[0] or "127.0.0.1"


async def get_or_create_anti_bot_settings(session: AsyncSession) -> AntiBotSettings:
    settings = await session.get(AntiBotSettings, 1)
    if settings is None:
        settings = AntiBotSettings(id=1, preset="BALANCED")
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


def create_anti_bot_router(
    sessions: async_sessionmaker[AsyncSession],
) -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["settings"])

    @router.get("/anti-bot")
    async def get_anti_bot() -> AntiBotSettingsResponse:
        async with sessions() as session:
            settings = await get_or_create_anti_bot_settings(session)
            return AntiBotSettingsResponse.model_validate(settings)

    @router.put("/anti-bot")
    async def update_anti_bot(
        payload: AntiBotSettingsUpdate,
    ) -> AntiBotSettingsResponse:
        async with sessions() as session:
            settings = await get_or_create_anti_bot_settings(session)
            updates = payload.model_dump(exclude_unset=True)
            chosen_preset = updates.get("preset")
            if chosen_preset in PRESET_DEFAULTS:
                for key, val in PRESET_DEFAULTS[chosen_preset].items():
                    setattr(settings, key, val)
            for key, value in updates.items():
                setattr(settings, key, value)
            if "edit_studio_host" in updates and updates["edit_studio_host"]:
                settings.edit_studio_host = normalize_host_input(str(updates["edit_studio_host"]))
            if settings.scroll_delay_max_ms < settings.scroll_delay_min_ms:
                settings.scroll_delay_max_ms = settings.scroll_delay_min_ms
            if settings.download_delay_max_ms < settings.download_delay_min_ms:
                settings.download_delay_max_ms = settings.download_delay_min_ms
            settings.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(settings)
            return AntiBotSettingsResponse.model_validate(settings)

    @router.get("/edit-studio")
    async def get_edit_studio_config() -> EditStudioConfigResponse:
        async with sessions() as session:
            settings = await get_or_create_anti_bot_settings(session)
            host = settings.edit_studio_host or "127.0.0.1"
            port = settings.edit_studio_port or 8000
            return EditStudioConfigResponse(
                host=host,
                port=port,
                base_url=format_edit_studio_base_url(host, port),
                updated_at=settings.updated_at,
            )

    @router.put("/edit-studio")
    async def update_edit_studio_config(
        payload: EditStudioConfigUpdate,
    ) -> EditStudioConfigResponse:
        async with sessions() as session:
            settings = await get_or_create_anti_bot_settings(session)
            settings.edit_studio_host = normalize_host_input(payload.host)
            settings.edit_studio_port = payload.port
            settings.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(settings)
            return EditStudioConfigResponse(
                host=settings.edit_studio_host,
                port=settings.edit_studio_port,
                base_url=format_edit_studio_base_url(
                    settings.edit_studio_host, settings.edit_studio_port
                ),
                updated_at=settings.updated_at,
            )

    return router
