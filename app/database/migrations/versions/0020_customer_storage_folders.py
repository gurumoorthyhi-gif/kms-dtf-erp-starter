"""Add stable customer storage folder metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_customer_storage_folders"
down_revision: str | None = "0019_cloud_drive_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("storage_prefix", sa.String(500), nullable=False, server_default=""),
    )
    op.add_column(
        "customers",
        sa.Column("google_drive_folder_id", sa.String(255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("customers", "google_drive_folder_id")
    op.drop_column("customers", "storage_prefix")
