"""Track optional Google Drive catalog entries for Backblaze objects."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_cloud_drive_catalog"
down_revision: str | None = "0018_customer_preferred_rate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cloud_files",
        sa.Column("google_drive_file_id", sa.String(255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("cloud_files", "google_drive_file_id")
