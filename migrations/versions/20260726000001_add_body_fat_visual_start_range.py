"""Add start range to visual body-fat profile selections.

Revision ID: 20260730000003
Revises: 20260730000002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260730000003"
down_revision = "20260730000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "body_fat_visual_profiles",
        sa.Column("start_range_id", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "check_bf_visual_start_range",
        "body_fat_visual_profiles",
        "start_range_id IN "
        "('male_8_12', 'male_13_16', 'male_17_20', 'male_21_24', "
        "'male_25_29', 'male_30_plus', 'female_18_21', 'female_22_25', "
        "'female_26_30', 'female_31_35', 'female_36_39', 'female_40_plus')",
    )
    op.drop_constraint(
        "check_bf_visual_ranges_match_sex",
        "body_fat_visual_profiles",
        type_="check",
    )
    op.create_check_constraint(
        "check_bf_visual_ranges_match_sex",
        "body_fat_visual_profiles",
        "(sex_at_selection = 'male' "
        "AND (start_range_id IS NULL OR start_range_id LIKE 'male_%') "
        "AND current_range_id LIKE 'male_%' "
        "AND (target_range_id IS NULL OR target_range_id LIKE 'male_%')) OR "
        "(sex_at_selection = 'female' "
        "AND (start_range_id IS NULL OR start_range_id LIKE 'female_%') "
        "AND current_range_id LIKE 'female_%' "
        "AND (target_range_id IS NULL OR target_range_id LIKE 'female_%'))",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_bf_visual_ranges_match_sex",
        "body_fat_visual_profiles",
        type_="check",
    )
    op.create_check_constraint(
        "check_bf_visual_ranges_match_sex",
        "body_fat_visual_profiles",
        "(sex_at_selection = 'male' AND current_range_id LIKE 'male_%' "
        "AND (target_range_id IS NULL OR target_range_id LIKE 'male_%')) OR "
        "(sex_at_selection = 'female' AND current_range_id LIKE 'female_%' "
        "AND (target_range_id IS NULL OR target_range_id LIKE 'female_%'))",
    )
    op.drop_constraint(
        "check_bf_visual_start_range",
        "body_fat_visual_profiles",
        type_="check",
    )
    op.drop_column("body_fat_visual_profiles", "start_range_id")
