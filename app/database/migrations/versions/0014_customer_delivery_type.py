"""Add courier/local delivery selection to customers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_customer_delivery_type"
down_revision: str | None = "0013_reports_backup_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "delivery_type",
            sa.String(length=20),
            nullable=False,
            server_default="Courier",
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "delivery_type")
