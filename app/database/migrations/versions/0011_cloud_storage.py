"""Add durable cloud file and offline queue metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_cloud_storage"
down_revision: str | None = "0010_packing_dispatch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cloud_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("object_key", sa.String(700), nullable=False),
        sa.Column("local_path", sa.String(700), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("transfer_state", sa.String(30), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cloud_files_object_key", "cloud_files", ["object_key"], unique=True)
    op.create_index("ix_cloud_files_transfer_state", "cloud_files", ["transfer_state"])


def downgrade() -> None:
    op.drop_index("ix_cloud_files_transfer_state", table_name="cloud_files")
    op.drop_index("ix_cloud_files_object_key", table_name="cloud_files")
    op.drop_table("cloud_files")
