"""Add district to customer addresses."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_customer_address_district"
down_revision: str | None = "0015_customer_preferred_courier"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_addresses",
        sa.Column(
            "district",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("customer_addresses", "district")
