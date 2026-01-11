"""
Feature flag database model for application-wide feature control.
"""
from sqlalchemy import Boolean, Column, String, DateTime

from src.domain.services.timezone_utils import utc_now
from src.infra.database.config import Base


class FeatureFlag(Base):
    """Database model for feature flags."""

    __tablename__ = "feature_flags"

    name = Column(String(255), primary_key=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)