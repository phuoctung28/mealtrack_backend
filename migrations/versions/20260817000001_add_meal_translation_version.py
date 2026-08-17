"""Track the translation contract used to create persisted meal translations."""

import sqlalchemy as sa
from alembic import op

revision = "20260817000001"
down_revision = "20260815000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a nullable version so pre-cutover rows are retranslated once."""
    op.add_column(
        "meal_translation",
        sa.Column("translation_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove the translation contract marker."""
    op.drop_column("meal_translation", "translation_version")
