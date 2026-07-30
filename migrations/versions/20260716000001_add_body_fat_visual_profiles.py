"""Add append-only visual body-fat profile selections.

Revision ID: 20260716000001
Revises: 20260702000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260716000001"
down_revision = "20260702000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_fat_visual_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("range_catalog_version", sa.Integer(), nullable=False),
        sa.Column("sex_at_selection", sa.String(length=6), nullable=False),
        sa.Column("current_range_id", sa.String(length=20), nullable=False),
        sa.Column("target_range_id", sa.String(length=20), nullable=True),
        sa.CheckConstraint("schema_version = 1", name="check_bf_visual_schema_version"),
        sa.CheckConstraint(
            "range_catalog_version = 1", name="check_bf_visual_catalog_version"
        ),
        sa.CheckConstraint(
            "sex_at_selection IN ('male', 'female')", name="check_bf_visual_sex"
        ),
        sa.CheckConstraint(
            "current_range_id IN "
            "('male_8_12', 'male_13_16', 'male_17_20', 'male_21_24', "
            "'male_25_29', 'male_30_plus', 'female_18_21', 'female_22_25', "
            "'female_26_30', 'female_31_35', 'female_36_39', 'female_40_plus')",
            name="check_bf_visual_current_range",
        ),
        sa.CheckConstraint(
            "target_range_id IN "
            "('male_8_12', 'male_13_16', 'male_17_20', 'male_21_24', "
            "'male_25_29', 'male_30_plus', 'female_18_21', 'female_22_25', "
            "'female_26_30', 'female_31_35', 'female_36_39', 'female_40_plus')",
            name="check_bf_visual_target_range",
        ),
        sa.CheckConstraint(
            "(sex_at_selection = 'male' AND current_range_id LIKE 'male_%' "
            "AND (target_range_id IS NULL OR target_range_id LIKE 'male_%')) OR "
            "(sex_at_selection = 'female' AND current_range_id LIKE 'female_%' "
            "AND (target_range_id IS NULL OR target_range_id LIKE 'female_%'))",
            name="check_bf_visual_ranges_match_sex",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_bf_visual_profiles_user_updated",
        "body_fat_visual_profiles",
        ["user_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_bf_visual_profiles_user_updated", "body_fat_visual_profiles")
    op.drop_table("body_fat_visual_profiles")
