"""Store the high-level product type selected during order intake."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_order_type"
down_revision: str | None = "0022_customer_code_prefixes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("order_type", sa.String(30), nullable=False, server_default="DTF"),
    )


def downgrade() -> None:
    op.drop_column("orders", "order_type")
