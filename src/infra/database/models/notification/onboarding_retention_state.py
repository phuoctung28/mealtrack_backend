"""ORM model for onboarding retention campaign state per user."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, text

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class OnboardingRetentionStateORM(Base):
    """Tracks when each user's D1-D3 campaign started and optional metadata.

    One row per user. The campaign window is D1 local date through D3 local date
    (3 days inclusive). Rows persist after the campaign ends for analytics.
    """

    __tablename__ = "onboarding_retention_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    campaign_started_at = Column(DateTime(timezone=True), nullable=False)
    campaign_timezone = Column(String(64), nullable=False, server_default="UTC")
    # Set by mobile when user completes the D1 mobility intent modal.
    tomorrow_mobility_type = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
