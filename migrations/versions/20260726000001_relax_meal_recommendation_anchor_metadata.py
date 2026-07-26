"""Relax meal recommendation anchor metadata constraint.

Revision ID: 20260726000001
Revises: 20260724000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726000001"
down_revision = "20260724000001"
branch_labels = None
depends_on = None


ANCHOR_METADATA_WITHOUT_ALGORITHM_VERSION = """
(
    id = batch_id
    AND user_id IS NOT NULL
    AND status IS NOT NULL
    AND timezone IS NOT NULL
    AND start_date IS NOT NULL
    AND target_calories IS NOT NULL
    AND operation IS NOT NULL
    AND idempotency_key IS NOT NULL
    AND request_fingerprint IS NOT NULL
) OR (
    id <> batch_id
    AND user_id IS NULL
    AND status IS NULL
    AND timezone IS NULL
    AND start_date IS NULL
    AND target_calories IS NULL
    AND operation IS NULL
    AND idempotency_key IS NULL
    AND request_fingerprint IS NULL
    AND superseded_at IS NULL
)
"""

ANCHOR_METADATA_WITH_ALGORITHM_VERSION = """
(
    id = batch_id
    AND user_id IS NOT NULL
    AND status IS NOT NULL
    AND timezone IS NOT NULL
    AND start_date IS NOT NULL
    AND target_calories IS NOT NULL
    AND algorithm_version IS NOT NULL
    AND operation IS NOT NULL
    AND idempotency_key IS NOT NULL
    AND request_fingerprint IS NOT NULL
) OR (
    id <> batch_id
    AND user_id IS NULL
    AND status IS NULL
    AND timezone IS NULL
    AND start_date IS NULL
    AND target_calories IS NULL
    AND algorithm_version IS NULL
    AND operation IS NULL
    AND idempotency_key IS NULL
    AND request_fingerprint IS NULL
    AND superseded_at IS NULL
)
"""


def upgrade() -> None:
    op.drop_constraint(
        "ck_meal_recommendations_anchor_metadata",
        "meal_recommendations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendations_anchor_metadata",
        "meal_recommendations",
        ANCHOR_METADATA_WITHOUT_ALGORITHM_VERSION,
    )


def downgrade() -> None:
    has_algorithm_version = op.get_bind().execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'meal_recommendations'
                  AND column_name = 'algorithm_version'
            )
            """
        )
    ).scalar_one()
    op.drop_constraint(
        "ck_meal_recommendations_anchor_metadata",
        "meal_recommendations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_meal_recommendations_anchor_metadata",
        "meal_recommendations",
        ANCHOR_METADATA_WITH_ALGORITHM_VERSION
        if has_algorithm_version
        else ANCHOR_METADATA_WITHOUT_ALGORITHM_VERSION,
    )
