"""Add inventory movements, suppliers, and purchases."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_inventory_purchases"
down_revision: str | None = "0007_production"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(14, 3), nullable=False),
        sa.Column("reorder_level", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("allow_negative", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_inventory_items_sku", "inventory_items", ["sku"], unique=True)
    op.create_index("ix_inventory_items_name", "inventory_items", ["name"])
    op.create_index("ix_inventory_items_item_type", "inventory_items", ["item_type"])
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "inventory_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id"), nullable=False
        ),
        sa.Column("movement_type", sa.String(40), nullable=False),
        sa.Column("quantity_change", sa.Numeric(14, 3), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 3), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_inventory_movements_inventory_item_id", "inventory_movements", ["inventory_item_id"]
    )
    op.create_index(
        "ix_inventory_movements_movement_type", "inventory_movements", ["movement_type"]
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("contact_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("gst_number", sa.String(20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_number", sa.String(30), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
    )
    op.create_index("ix_purchases_purchase_number", "purchases", ["purchase_number"], unique=True)
    op.create_index("ix_purchases_supplier_id", "purchases", ["supplier_id"])
    op.create_index("ix_purchases_status", "purchases", ["status"])
    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "purchase_id",
            sa.Integer(),
            sa.ForeignKey("purchases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inventory_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id"), nullable=False
        ),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("received_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_items_purchase_id", table_name="purchase_items")
    op.drop_table("purchase_items")
    op.drop_index("ix_purchases_status", table_name="purchases")
    op.drop_index("ix_purchases_supplier_id", table_name="purchases")
    op.drop_index("ix_purchases_purchase_number", table_name="purchases")
    op.drop_table("purchases")
    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_index("ix_suppliers_code", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_inventory_movements_movement_type", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_inventory_item_id", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_items_item_type", table_name="inventory_items")
    op.drop_index("ix_inventory_items_name", table_name="inventory_items")
    op.drop_index("ix_inventory_items_sku", table_name="inventory_items")
    op.drop_table("inventory_items")
