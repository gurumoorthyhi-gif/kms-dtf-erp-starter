"""Add packing, dispatch, history, and notification events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_packing_dispatch"
down_revision: str | None = "0009_sales_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "packings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("packing_number", sa.String(30), nullable=False),
        sa.Column("packing_list", sa.Text(), nullable=False),
        sa.Column("package_count", sa.Integer(), nullable=False),
        sa.Column("package_weight", sa.Numeric(12, 3), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("packed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_packings_order_id", "packings", ["order_id"], unique=True)
    op.create_index("ix_packings_packing_number", "packings", ["packing_number"], unique=True)
    op.create_index("ix_packings_is_complete", "packings", ["is_complete"])
    op.create_table(
        "dispatches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("packing_id", sa.Integer(), sa.ForeignKey("packings.id"), nullable=False),
        sa.Column("dispatch_number", sa.String(30), nullable=False),
        sa.Column("courier", sa.String(80), nullable=False),
        sa.Column("tracking_number", sa.String(100), nullable=False),
        sa.Column("dispatch_date", sa.Date(), nullable=False),
        sa.Column("delivery_status", sa.String(30), nullable=False),
        sa.Column("shipping_label_path", sa.String(500), nullable=False),
        sa.Column("proof_of_dispatch_path", sa.String(500), nullable=False),
        sa.Column("override_authorized", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_dispatches_order_id", "dispatches", ["order_id"], unique=True)
    op.create_index("ix_dispatches_packing_id", "dispatches", ["packing_id"])
    op.create_index("ix_dispatches_dispatch_number", "dispatches", ["dispatch_number"], unique=True)
    op.create_index("ix_dispatches_tracking_number", "dispatches", ["tracking_number"])
    op.create_index("ix_dispatches_delivery_status", "dispatches", ["delivery_status"])
    op.create_table(
        "dispatch_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dispatch_id",
            sa.Integer(),
            sa.ForeignKey("dispatches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_events_dispatch_id", "dispatch_events", ["dispatch_id"])
    op.create_table(
        "customer_notification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("dispatch_id", sa.Integer(), sa.ForeignKey("dispatches.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_customer_notification_events_order_id", "customer_notification_events", ["order_id"]
    )
    op.create_index(
        "ix_customer_notification_events_dispatch_id",
        "customer_notification_events",
        ["dispatch_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_notification_events_dispatch_id", table_name="customer_notification_events"
    )
    op.drop_index(
        "ix_customer_notification_events_order_id", table_name="customer_notification_events"
    )
    op.drop_table("customer_notification_events")
    op.drop_index("ix_dispatch_events_dispatch_id", table_name="dispatch_events")
    op.drop_table("dispatch_events")
    op.drop_index("ix_dispatches_delivery_status", table_name="dispatches")
    op.drop_index("ix_dispatches_tracking_number", table_name="dispatches")
    op.drop_index("ix_dispatches_dispatch_number", table_name="dispatches")
    op.drop_index("ix_dispatches_packing_id", table_name="dispatches")
    op.drop_index("ix_dispatches_order_id", table_name="dispatches")
    op.drop_table("dispatches")
    op.drop_index("ix_packings_is_complete", table_name="packings")
    op.drop_index("ix_packings_packing_number", table_name="packings")
    op.drop_index("ix_packings_order_id", table_name="packings")
    op.drop_table("packings")
