"""Upgrade schema for Dashboard v2: metadata, bookmarks, visual scheduler, anti-bot, and detailed logs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261027_03"
down_revision: str | Sequence[str] | None = "20261026_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_crawl_targets_type", "crawl_targets", type_="check")
    op.create_check_constraint(
        "ck_crawl_targets_type",
        "crawl_targets",
        "target_type IN ('CHANNEL', 'KEYWORD', 'COLLECT')",
    )
    op.add_column(
        "crawl_targets",
        sa.Column("schedule_type", sa.String(32), nullable=False, server_default="CRON"),
    )
    op.add_column(
        "crawl_targets",
        sa.Column(
            "schedule_config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "crawl_targets",
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crawl_targets",
        sa.Column("auto_download", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        "ck_crawl_targets_schedule_type",
        "crawl_targets",
        "schedule_type IN ('INTERVAL', 'DAILY', 'ONCE', 'CRON', 'MANUAL')",
    )

    op.add_column(
        "douyin_videos",
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("douyin_videos", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("douyin_videos", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("douyin_videos", sa.Column("music_title", sa.String(255), nullable=True))
    op.add_column("douyin_videos", sa.Column("music_author", sa.String(255), nullable=True))
    op.add_column(
        "douyin_videos",
        sa.Column("is_bookmarked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "douyin_videos",
        sa.Column("bookmarked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "douyin_videos",
        sa.Column("bookmark_collection", sa.String(128), nullable=True),
    )
    op.add_column("douyin_videos", sa.Column("bookmark_note", sa.Text(), nullable=True))
    op.add_column("douyin_videos", sa.Column("edit_item_id", sa.String(64), nullable=True))
    op.add_column("douyin_videos", sa.Column("edit_list_id", sa.String(64), nullable=True))
    op.create_index("ix_douyin_videos_is_bookmarked", "douyin_videos", ["is_bookmarked"])
    op.create_index("ix_douyin_videos_duration_ms", "douyin_videos", ["duration_ms"])

    op.drop_constraint("ck_crawl_logs_status", "crawl_logs", type_="check")
    op.create_check_constraint(
        "ck_crawl_logs_status",
        "crawl_logs",
        "status IN ('SCHEDULED', 'RUNNING', 'SUCCESS', 'FAILED', 'CAPTCHA_BLOCKED')",
    )
    op.add_column(
        "crawl_logs",
        sa.Column("job_type", sa.String(32), nullable=False, server_default="TARGET_CRAWL"),
    )
    op.add_column(
        "crawl_logs",
        sa.Column("trigger_type", sa.String(32), nullable=False, server_default="MANUAL"),
    )
    op.add_column("crawl_logs", sa.Column("input_summary", sa.Text(), nullable=True))
    op.add_column(
        "crawl_logs",
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "ck_crawl_logs_job_type",
        "crawl_logs",
        "job_type IN ('TARGET_CRAWL', 'SINGLE_CRAWL', 'DOWNLOAD')",
    )
    op.create_check_constraint(
        "ck_crawl_logs_trigger_type",
        "crawl_logs",
        "trigger_type IN ('SCHEDULED', 'MANUAL', 'ONCE', 'RETRY')",
    )

    op.create_table(
        "anti_bot_settings",
        sa.Column("id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("preset", sa.String(32), nullable=False, server_default="BALANCED"),
        sa.Column("scroll_delay_min_ms", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("scroll_delay_max_ms", sa.Integer(), nullable=False, server_default="3500"),
        sa.Column("download_delay_min_ms", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("download_delay_max_ms", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("cooldown_between_targets_sec", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("stealth_mode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("human_scroll", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_stop_on_captcha", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_pages_per_run", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("proxy_url", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("id = 1", name="ck_anti_bot_settings_singleton"),
        sa.CheckConstraint(
            "preset IN ('SAFE', 'BALANCED', 'FAST', 'CUSTOM')",
            name="ck_anti_bot_settings_preset",
        ),
    )


def downgrade() -> None:
    op.drop_table("anti_bot_settings")
    op.drop_constraint("ck_crawl_logs_trigger_type", "crawl_logs", type_="check")
    op.drop_constraint("ck_crawl_logs_job_type", "crawl_logs", type_="check")
    op.drop_column("crawl_logs", "payload")
    op.drop_column("crawl_logs", "input_summary")
    op.drop_column("crawl_logs", "trigger_type")
    op.drop_column("crawl_logs", "job_type")
    op.drop_constraint("ck_crawl_logs_status", "crawl_logs", type_="check")
    op.create_check_constraint(
        "ck_crawl_logs_status",
        "crawl_logs",
        "status IN ('RUNNING', 'SUCCESS', 'FAILED')",
    )

    op.drop_index("ix_douyin_videos_duration_ms", table_name="douyin_videos")
    op.drop_index("ix_douyin_videos_is_bookmarked", table_name="douyin_videos")
    op.drop_column("douyin_videos", "edit_list_id")
    op.drop_column("douyin_videos", "edit_item_id")
    op.drop_column("douyin_videos", "bookmark_note")
    op.drop_column("douyin_videos", "bookmark_collection")
    op.drop_column("douyin_videos", "bookmarked_at")
    op.drop_column("douyin_videos", "is_bookmarked")
    op.drop_column("douyin_videos", "music_author")
    op.drop_column("douyin_videos", "music_title")
    op.drop_column("douyin_videos", "height")
    op.drop_column("douyin_videos", "width")
    op.drop_column("douyin_videos", "duration_ms")

    op.drop_constraint("ck_crawl_targets_schedule_type", "crawl_targets", type_="check")
    op.drop_column("crawl_targets", "auto_download")
    op.drop_column("crawl_targets", "run_at")
    op.drop_column("crawl_targets", "schedule_config")
    op.drop_column("crawl_targets", "schedule_type")
    op.drop_constraint("ck_crawl_targets_type", "crawl_targets", type_="check")
    op.create_check_constraint(
        "ck_crawl_targets_type",
        "crawl_targets",
        "target_type IN ('CHANNEL', 'KEYWORD')",
    )
