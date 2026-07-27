"""Add preferred courier details to customers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_customer_preferred_courier"
down_revision: str | None = "0014_customer_delivery_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "preferred_courier",
            sa.String(length=30),
            nullable=False,
            server_default="ST",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "other_transport_name",
            sa.String(length=120),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "other_transport_name")
    op.drop_column("customers", "preferred_courier")
