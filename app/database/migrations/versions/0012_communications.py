"""Add provider-neutral WhatsApp and email conversations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_communications"
down_revision: str | None = "0011_cloud_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "communication_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("provider_message_id", sa.String(200), nullable=False),
        sa.Column("thread_key", sa.String(200), nullable=False),
        sa.Column("sender", sa.String(254), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column(
            "reply_to_id", sa.Integer(), sa.ForeignKey("communication_messages.id"), nullable=True
        ),
        sa.Column(
            "forwarded_from_id",
            sa.Integer(),
            sa.ForeignKey("communication_messages.id"),
            nullable=True,
        ),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, columns, unique in (
        ("ix_communication_messages_channel", ["channel"], False),
        ("ix_communication_messages_direction", ["direction"], False),
        ("ix_communication_messages_provider_message_id", ["provider_message_id"], True),
        ("ix_communication_messages_thread_key", ["thread_key"], False),
        ("ix_communication_messages_customer_id", ["customer_id"], False),
        ("ix_communication_messages_order_id", ["order_id"], False),
    ):
        op.create_index(name, "communication_messages", columns, unique=unique)
    op.create_table(
        "communication_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("communication_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(700), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
    )
    op.create_index(
        "ix_communication_attachments_message_id", "communication_attachments", ["message_id"]
    )
    op.create_table(
        "message_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("template_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
    )
    op.create_index("ix_message_templates_channel", "message_templates", ["channel"])
    op.create_index("ix_message_templates_template_type", "message_templates", ["template_type"])


def downgrade() -> None:
    op.drop_index("ix_message_templates_template_type", table_name="message_templates")
    op.drop_index("ix_message_templates_channel", table_name="message_templates")
    op.drop_table("message_templates")
    op.drop_index("ix_communication_attachments_message_id", table_name="communication_attachments")
    op.drop_table("communication_attachments")
    for name in (
        "ix_communication_messages_order_id",
        "ix_communication_messages_customer_id",
        "ix_communication_messages_thread_key",
        "ix_communication_messages_provider_message_id",
        "ix_communication_messages_direction",
        "ix_communication_messages_channel",
    ):
        op.drop_index(name, table_name="communication_messages")
    op.drop_table("communication_messages")
