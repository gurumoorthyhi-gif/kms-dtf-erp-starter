"""Add production jobs, immutable events, and quality checks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_production"
down_revision: str | None = "0006_gang_sheets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("gang_sheet_id", sa.Integer(), sa.ForeignKey("gang_sheets.id"), nullable=True),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("machine_name", sa.String(100), nullable=False),
        sa.Column("operator_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("pause_reason", sa.Text(), nullable=False),
        sa.Column("reprint_count", sa.Integer(), nullable=False),
        sa.Column("wastage_metres", sa.Numeric(10, 3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, columns in (
        ("ix_production_jobs_order_id", ["order_id"]),
        ("ix_production_jobs_stage", ["stage"]),
        ("ix_production_jobs_priority", ["priority"]),
        ("ix_production_jobs_due_date", ["due_date"]),
    ):
        op.create_index(name, "production_jobs", columns)
    op.create_table(
        "production_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "production_job_id",
            sa.Integer(),
            sa.ForeignKey("production_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_stage", sa.String(40), nullable=True),
        sa.Column("to_stage", sa.String(40), nullable=True),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_production_events_production_job_id", "production_events", ["production_job_id"]
    )
    op.create_table(
        "quality_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "production_job_id",
            sa.Integer(),
            sa.ForeignKey("production_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("print_quality_ok", sa.Boolean(), nullable=False),
        sa.Column("colour_ok", sa.Boolean(), nullable=False),
        sa.Column("curing_ok", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("inspector_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_checks_production_job_id", "quality_checks", ["production_job_id"])


def downgrade() -> None:
    op.drop_index("ix_quality_checks_production_job_id", table_name="quality_checks")
    op.drop_table("quality_checks")
    op.drop_index("ix_production_events_production_job_id", table_name="production_events")
    op.drop_table("production_events")
    for name in (
        "ix_production_jobs_due_date",
        "ix_production_jobs_priority",
        "ix_production_jobs_stage",
        "ix_production_jobs_order_id",
    ):
        op.drop_index(name, table_name="production_jobs")
    op.drop_table("production_jobs")
