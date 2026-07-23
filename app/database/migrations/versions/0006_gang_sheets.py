"""Add gang sheets and positioned artwork items."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_gang_sheets"
down_revision: str | None = "0005_artwork_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gang_sheets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("width_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("length_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("margin_mm", sa.Numeric(8, 2), nullable=False),
        sa.Column("spacing_mm", sa.Numeric(8, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "gang_sheet_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "gang_sheet_id",
            sa.Integer(),
            sa.ForeignKey("gang_sheets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artwork_version_id",
            sa.Integer(),
            sa.ForeignKey("artwork_versions.id"),
            nullable=False,
        ),
        sa.Column("x_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("y_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("width_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("height_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("rotation_degrees", sa.Integer(), nullable=False),
        sa.Column("z_index", sa.Integer(), nullable=False),
    )
    op.create_index("ix_gang_sheet_items_gang_sheet_id", "gang_sheet_items", ["gang_sheet_id"])


def downgrade() -> None:
    op.drop_index("ix_gang_sheet_items_gang_sheet_id", table_name="gang_sheet_items")
    op.drop_table("gang_sheet_items")
    op.drop_table("gang_sheets")
