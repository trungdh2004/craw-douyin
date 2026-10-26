"""Allow a Douyin post to belong to multiple crawl targets."""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20261026_02"
down_revision: str | Sequence[str] | None = "20261026_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_sources",
        sa.Column("aweme_id", sa.String(64), sa.ForeignKey("douyin_videos.aweme_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("crawl_targets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("INSERT INTO video_sources (aweme_id, target_id) SELECT aweme_id, target_id FROM douyin_videos WHERE target_id IS NOT NULL")


def downgrade() -> None:
    op.drop_table("video_sources")
