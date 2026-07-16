"""Persistence model for append-only visual body-fat profile selections."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, String

from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class BodyFatVisualProfile(Base, BaseMixin):
    """Stores visual selections independently from measured body-fat data."""

    __tablename__ = "body_fat_visual_profiles"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    schema_version = Column(Integer, nullable=False)
    range_catalog_version = Column(Integer, nullable=False)
    sex_at_selection = Column(String(6), nullable=False)
    current_range_id = Column(String(20), nullable=False)
    target_range_id = Column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint("schema_version = 1", name="check_bf_visual_schema_version"),
        CheckConstraint(
            "range_catalog_version = 1", name="check_bf_visual_catalog_version"
        ),
        CheckConstraint(
            "sex_at_selection IN ('male', 'female')", name="check_bf_visual_sex"
        ),
        CheckConstraint(
            "current_range_id IN "
            "('male_8_12', 'male_13_16', 'male_17_20', 'male_21_24', "
            "'male_25_29', 'male_30_plus', 'female_18_21', 'female_22_25', "
            "'female_26_30', 'female_31_35', 'female_36_39', 'female_40_plus')",
            name="check_bf_visual_current_range",
        ),
        CheckConstraint(
            "target_range_id IN "
            "('male_8_12', 'male_13_16', 'male_17_20', 'male_21_24', "
            "'male_25_29', 'male_30_plus', 'female_18_21', 'female_22_25', "
            "'female_26_30', 'female_31_35', 'female_36_39', 'female_40_plus')",
            name="check_bf_visual_target_range",
        ),
        CheckConstraint(
            "(sex_at_selection = 'male' AND current_range_id LIKE 'male_%' "
            "AND (target_range_id IS NULL OR target_range_id LIKE 'male_%')) OR "
            "(sex_at_selection = 'female' AND current_range_id LIKE 'female_%' "
            "AND (target_range_id IS NULL OR target_range_id LIKE 'female_%'))",
            name="check_bf_visual_ranges_match_sex",
        ),
        Index("idx_bf_visual_profiles_user_updated", "user_id", "updated_at"),
    )
