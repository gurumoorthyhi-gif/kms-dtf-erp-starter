"""Link uploaded customer designs to their saved order."""

import sqlalchemy as sa
from alembic import op

revision: str = "0024_order_design_files"
down_revision: str | None = "0023_order_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("design_file_ids", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("orders", "design_file_ids")
