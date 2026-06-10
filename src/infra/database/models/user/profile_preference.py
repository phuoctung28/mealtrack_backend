"""Normalized user profile preference values."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class UserProfilePreference(Base, BaseMixin):
    """Typed preference value attached to a user profile."""

    __tablename__ = "user_profile_preferences"

    profile_id = Column(
        String(36),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    preference_type = Column(String(40), nullable=False)
    value = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    profile = relationship("UserProfile", back_populates="preference_entries")

    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "preference_type",
            "value",
            name="uq_user_profile_preference_value",
        ),
        Index(
            "idx_user_profile_preferences_position",
            "profile_id",
            "preference_type",
            "position",
        ),
    )
