"""Add landmark to customer addresses."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_customer_address_landmark"
down_revision: str | None = "0016_customer_address_district"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_addresses",
        sa.Column(
            "landmark",
            sa.String(length=200),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("customer_addresses", "landmark")
