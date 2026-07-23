"""Add artwork library, versions, and approvals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_artwork_library"
down_revision: str | None = "0004_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("tags", sa.String(500), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artworks_title", "artworks", ["title"])
    op.create_index("ix_artworks_tags", "artworks", ["tags"])
    op.create_index("ix_artworks_customer_id", "artworks", ["customer_id"])
    op.create_index("ix_artworks_order_id", "artworks", ["order_id"])
    op.create_table(
        "artwork_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "artwork_id",
            sa.Integer(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("original_path", sa.String(500), nullable=False),
        sa.Column("preview_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("dpi_x", sa.Integer(), nullable=False),
        sa.Column("dpi_y", sa.Integer(), nullable=False),
        sa.Column("has_transparency", sa.Boolean(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artwork_id", "version_number"),
    )
    op.create_index("ix_artwork_versions_artwork_id", "artwork_versions", ["artwork_id"])
    op.create_table(
        "artwork_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "artwork_version_id",
            sa.Integer(),
            sa.ForeignKey("artwork_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_artwork_approvals_artwork_version_id",
        "artwork_approvals",
        ["artwork_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_artwork_approvals_artwork_version_id", table_name="artwork_approvals")
    op.drop_table("artwork_approvals")
    op.drop_index("ix_artwork_versions_artwork_id", table_name="artwork_versions")
    op.drop_table("artwork_versions")
    op.drop_index("ix_artworks_order_id", table_name="artworks")
    op.drop_index("ix_artworks_customer_id", table_name="artworks")
    op.drop_index("ix_artworks_tags", table_name="artworks")
    op.drop_index("ix_artworks_title", table_name="artworks")
    op.drop_table("artworks")
