"""Add backup history and immutable audit records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_reports_backup_audit"
down_revision: str | None = "0012_communications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backup_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backup_path", sa.String(700), nullable=False),
        sa.Column("backup_type", sa.String(30), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("cloud_object_key", sa.String(700), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_backup_history_backup_type", "backup_history", ["backup_type"])
    op.create_table(
        "audit_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, columns in (
        ("ix_audit_records_actor_user_id", ["actor_user_id"]),
        ("ix_audit_records_action", ["action"]),
        ("ix_audit_records_entity_type", ["entity_type"]),
        ("ix_audit_records_created_at", ["created_at"]),
    ):
        op.create_index(name, "audit_records", columns)


def downgrade() -> None:
    for name in (
        "ix_audit_records_created_at",
        "ix_audit_records_entity_type",
        "ix_audit_records_action",
        "ix_audit_records_actor_user_id",
    ):
        op.drop_index(name, table_name="audit_records")
    op.drop_table("audit_records")
    op.drop_index("ix_backup_history_backup_type", table_name="backup_history")
    op.drop_table("backup_history")
