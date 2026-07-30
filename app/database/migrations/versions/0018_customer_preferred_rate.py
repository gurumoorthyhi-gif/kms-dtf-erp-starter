"""Add preferred rate to customers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_customer_preferred_rate"
down_revision: str | None = "0017_customer_address_landmark"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "preferred_rate",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "preferred_rate")
