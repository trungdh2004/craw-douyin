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
        CheckConstraint("target_type IN ('CHANNEL', 'KEYWORD')", name="ck_crawl_targets_type"),
        CheckConstraint("last_status IN ('IDLE', 'RUNNING', 'SUCCESS', 'FAILED')", name="ck_crawl_targets_status"),
        CheckConstraint("max_items_per_run > 0", name="ck_crawl_targets_max_items"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    target_type: Mapped[str] = mapped_column(String(32))
    target_value: Mapped[str] = mapped_column(Text)
    cron_expr: Mapped[str] = mapped_column(String(64), default="0 */6 * * *", server_default="0 */6 * * *")
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
    cover_remote_url: Mapped[str | None] = mapped_column(Text)
    cover_local_path: Mapped[str | None] = mapped_column(Text)
    raw_video_url: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    download_status: Mapped[str] = mapped_column(String(32), default="NONE", server_default="NONE")
    video_local_path: Mapped[str | None] = mapped_column(Text)
    download_error: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    __table_args__ = (
        CheckConstraint("status IN ('RUNNING', 'SUCCESS', 'FAILED')", name="ck_crawl_logs_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_targets.id", ondelete="CASCADE"), index=True)
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
