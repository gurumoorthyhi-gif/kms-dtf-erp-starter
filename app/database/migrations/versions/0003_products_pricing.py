"""Add products and configurable pricing."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_products_pricing"
down_revision: str | None = "0002_customers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column(
            "category_id", sa.Integer(), sa.ForeignKey("product_categories.id"), nullable=False
        ),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("size", sa.String(40), nullable=False),
        sa.Column("colour", sa.String(60), nullable=False),
        sa.Column("gsm", sa.String(20), nullable=False),
        sa.Column("style", sa.String(80), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_products_code", "products", ["code"], unique=True)
    op.create_table(
        "price_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("minimum_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table(
        "discount_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("minimum_subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "tax_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tax_configurations")
    op.drop_table("discount_rules")
    op.drop_table("price_rules")
    op.drop_index("ix_products_code", table_name="products")
    op.drop_table("products")
    op.drop_table("product_categories")
