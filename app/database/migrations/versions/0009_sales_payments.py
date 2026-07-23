"""Add sales documents, payments, and credit notes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_sales_payments"
down_revision: str | None = "0008_inventory_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_number", sa.String(30), nullable=False),
        sa.Column("document_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("converted_from_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("credit_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invoices_document_number", "invoices", ["document_number"], unique=True)
    op.create_index("ix_invoices_document_type", "invoices", ["document_type"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_number", sa.String(30), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payments_payment_number", "payments", ["payment_number"], unique=True)
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_table(
        "credit_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("credit_number", sa.String(30), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credit_notes_credit_number", "credit_notes", ["credit_number"], unique=True)
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_notes_invoice_id", table_name="credit_notes")
    op.drop_index("ix_credit_notes_credit_number", table_name="credit_notes")
    op.drop_table("credit_notes")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_index("ix_payments_payment_number", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_document_type", table_name="invoices")
    op.drop_index("ix_invoices_document_number", table_name="invoices")
    op.drop_table("invoices")
