"""Rename local and courier customer code prefixes."""

from collections.abc import Sequence

from alembic import op

revision: str = "0022_customer_code_prefixes"
down_revision: str | None = "0021_customer_storage_dates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Storage prefixes deliberately remain unchanged because they identify
    # existing Backblaze and Google Drive locations.
    op.execute(
        """
        UPDATE customers
        SET code = CASE
            WHEN code LIKE 'LO____' THEN 'LC' || SUBSTR(code, 3)
            WHEN code LIKE 'CO____' THEN 'CR' || SUBSTR(code, 3)
            ELSE code
        END
        WHERE code LIKE 'LO____' OR code LIKE 'CO____'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE customers
        SET code = CASE
            WHEN code LIKE 'LC____' THEN 'LO' || SUBSTR(code, 3)
            WHEN code LIKE 'CR____' THEN 'CO' || SUBSTR(code, 3)
            ELSE code
        END
        WHERE code LIKE 'LC____' OR code LIKE 'CR____'
        """
    )
