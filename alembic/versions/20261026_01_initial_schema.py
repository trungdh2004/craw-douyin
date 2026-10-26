"""Create crawler storage schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261026_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crawl_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_value", sa.Text(), nullable=False),
        sa.Column("cron_expr", sa.String(64), nullable=False, server_default="0 */6 * * *"),
        sa.Column("max_items_per_run", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_status", sa.String(32), nullable=False, server_default="IDLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('CHANNEL', 'KEYWORD')", name="ck_crawl_targets_type"),
        sa.CheckConstraint("last_status IN ('IDLE', 'RUNNING', 'SUCCESS', 'FAILED')", name="ck_crawl_targets_status"),
        sa.CheckConstraint("max_items_per_run > 0", name="ck_crawl_targets_max_items"),
    )
    op.create_table(
        "douyin_videos",
        sa.Column("aweme_id", sa.String(64), primary_key=True),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("crawl_targets.id", ondelete="SET NULL")),
        sa.Column("aweme_type", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hashtags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_sec_uid", sa.String(255), nullable=False),
        sa.Column("author_nickname", sa.String(255), nullable=False),
        sa.Column("author_avatar", sa.Text()),
        sa.Column("digg_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("collect_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cover_remote_url", sa.Text()),
        sa.Column("cover_local_path", sa.Text()),
        sa.Column("raw_video_url", sa.Text()),
        sa.Column("image_urls", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("download_status", sa.String(32), nullable=False, server_default="NONE"),
        sa.Column("video_local_path", sa.Text()),
        sa.Column("download_error", sa.Text()),
        sa.Column("downloaded_at", sa.DateTime(timezone=True)),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("download_status IN ('NONE', 'DOWNLOADING', 'COMPLETED', 'FAILED')", name="ck_douyin_videos_download_status"),
    )
    op.create_index("ix_douyin_videos_target_id", "douyin_videos", ["target_id"])
    op.create_index("ix_douyin_videos_create_time", "douyin_videos", ["create_time"])
    op.create_index("ix_douyin_videos_crawled_at", "douyin_videos", ["crawled_at"])
    op.create_table(
        "crawl_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("crawl_targets.id", ondelete="CASCADE")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("new_videos_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_videos_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint("status IN ('RUNNING', 'SUCCESS', 'FAILED')", name="ck_crawl_logs_status"),
    )
    op.create_index("ix_crawl_logs_target_id", "crawl_logs", ["target_id"])
    op.create_index("ix_crawl_logs_started_at", "crawl_logs", ["started_at"])


def downgrade() -> None:
    op.drop_table("crawl_logs")
    op.drop_table("douyin_videos")
    op.drop_table("crawl_targets")
