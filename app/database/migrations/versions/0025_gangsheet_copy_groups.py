"""Persist Production Studio copy groups and mirror state."""

import sqlalchemy as sa
from alembic import op

revision: str = "0025_gangsheet_copy_groups"
down_revision: str | None = "0024_order_design_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gang_sheet_items",
        sa.Column("copy_group_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "gang_sheet_items",
        sa.Column("mirrored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_gang_sheet_items_copy_group_id",
        "gang_sheet_items",
        ["copy_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_gang_sheet_items_copy_group_id", table_name="gang_sheet_items")
    op.drop_column("gang_sheet_items", "mirrored")
    op.drop_column("gang_sheet_items", "copy_group_id")
