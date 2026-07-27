"""Track explicitly created customer date folders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_customer_storage_dates"
down_revision: str | None = "0020_customer_storage_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_storage_dates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_date", sa.Date(), nullable=False),
        sa.Column(
            "google_drive_folder_id",
            sa.String(255),
            nullable=False,
            server_default="",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "folder_date"),
    )
    op.create_index(
        "ix_customer_storage_dates_customer_id",
        "customer_storage_dates",
        ["customer_id"],
    )
    op.create_index(
        "ix_customer_storage_dates_folder_date",
        "customer_storage_dates",
        ["folder_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_storage_dates_folder_date",
        table_name="customer_storage_dates",
    )
    op.drop_index(
        "ix_customer_storage_dates_customer_id",
        table_name="customer_storage_dates",
    )
    op.drop_table("customer_storage_dates")
