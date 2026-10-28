from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CrawlTarget(Base):
    __tablename__ = "crawl_targets"
    __table_args__ = (
        CheckConstraint("target_type IN ('CHANNEL', 'KEYWORD', 'COLLECT')", name="ck_crawl_targets_type"),
        CheckConstraint("last_status IN ('IDLE', 'RUNNING', 'SUCCESS', 'FAILED')", name="ck_crawl_targets_status"),
        CheckConstraint("max_items_per_run > 0", name="ck_crawl_targets_max_items"),
        CheckConstraint(
            "schedule_type IN ('INTERVAL', 'DAILY', 'ONCE', 'CRON', 'MANUAL')",
            name="ck_crawl_targets_schedule_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    target_type: Mapped[str] = mapped_column(String(32))
    target_value: Mapped[str] = mapped_column(Text)
    cron_expr: Mapped[str] = mapped_column(String(64), default="0 */6 * * *", server_default="0 */6 * * *")
    schedule_type: Mapped[str] = mapped_column(String(32), default="CRON", server_default="CRON")
    schedule_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_download: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    max_items_per_run: Mapped[int] = mapped_column(default=50, server_default="50")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(32), default="IDLE", server_default="IDLE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DouyinVideo(Base):
    __tablename__ = "douyin_videos"
    __table_args__ = (
        CheckConstraint("download_status IN ('NONE', 'DOWNLOADING', 'COMPLETED', 'FAILED')", name="ck_douyin_videos_download_status"),
    )

    aweme_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_targets.id", ondelete="SET NULL"), index=True)
    aweme_type: Mapped[int] = mapped_column(default=0, server_default="0")
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    hashtags: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default="[]")
    create_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    author_sec_uid: Mapped[str] = mapped_column(String(255))
    author_nickname: Mapped[str] = mapped_column(String(255))
    author_avatar: Mapped[str | None] = mapped_column(Text)
    digg_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    share_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    collect_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    music_title: Mapped[str | None] = mapped_column(String(255))
    music_author: Mapped[str | None] = mapped_column(String(255))
    cover_remote_url: Mapped[str | None] = mapped_column(Text)
    cover_local_path: Mapped[str | None] = mapped_column(Text)
    raw_video_url: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    download_status: Mapped[str] = mapped_column(String(32), default="NONE", server_default="NONE")
    video_local_path: Mapped[str | None] = mapped_column(Text)
    download_error: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    bookmarked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bookmark_collection: Mapped[str | None] = mapped_column(String(128))
    bookmark_note: Mapped[str | None] = mapped_column(Text)
    edit_item_id: Mapped[str | None] = mapped_column(String(64))
    edit_list_id: Mapped[str | None] = mapped_column(String(64))
    edit_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    edit_status: Mapped[str | None] = mapped_column(String(32))
    edit_error: Mapped[str | None] = mapped_column(Text)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SCHEDULED', 'RUNNING', 'SUCCESS', 'FAILED', 'CAPTCHA_BLOCKED')",
            name="ck_crawl_logs_status",
        ),
        CheckConstraint(
            "job_type IN ('TARGET_CRAWL', 'SINGLE_CRAWL', 'DOWNLOAD')",
            name="ck_crawl_logs_job_type",
        ),
        CheckConstraint(
            "trigger_type IN ('SCHEDULED', 'MANUAL', 'ONCE', 'RETRY')",
            name="ck_crawl_logs_trigger_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_targets.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(32), default="TARGET_CRAWL", server_default="TARGET_CRAWL")
    trigger_type: Mapped[str] = mapped_column(String(32), default="MANUAL", server_default="MANUAL")
    input_summary: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    new_videos_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_videos_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)


class VideoSource(Base):
    __tablename__ = "video_sources"

    aweme_id: Mapped[str] = mapped_column(ForeignKey("douyin_videos.aweme_id", ondelete="CASCADE"), primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("crawl_targets.id", ondelete="CASCADE"), primary_key=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AntiBotSettings(Base):
    __tablename__ = "anti_bot_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_anti_bot_settings_singleton"),
        CheckConstraint(
            "preset IN ('SAFE', 'BALANCED', 'FAST', 'CUSTOM')",
            name="ck_anti_bot_settings_preset",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, server_default="1")
    preset: Mapped[str] = mapped_column(String(32), default="BALANCED", server_default="BALANCED")
    scroll_delay_min_ms: Mapped[int] = mapped_column(Integer, default=1500, server_default="1500")
    scroll_delay_max_ms: Mapped[int] = mapped_column(Integer, default=3500, server_default="3500")
    download_delay_min_ms: Mapped[int] = mapped_column(Integer, default=500, server_default="500")
    download_delay_max_ms: Mapped[int] = mapped_column(Integer, default=1500, server_default="1500")
    cooldown_between_targets_sec: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    stealth_mode: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    human_scroll: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    auto_stop_on_captcha: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    headless_mode: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    max_pages_per_run: Mapped[int] = mapped_column(Integer, default=25, server_default="25")
    user_agent: Mapped[str | None] = mapped_column(Text)
    proxy_url: Mapped[str | None] = mapped_column(Text)
    edit_studio_host: Mapped[str] = mapped_column(String(255), default="127.0.0.1", server_default="127.0.0.1")
    edit_studio_port: Mapped[int] = mapped_column(Integer, default=8000, server_default="8000")
    admin_username: Mapped[str] = mapped_column(String(128), default="admin", server_default="admin")
    admin_password_hash: Mapped[str | None] = mapped_column(Text)
    admin_session_secret: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
