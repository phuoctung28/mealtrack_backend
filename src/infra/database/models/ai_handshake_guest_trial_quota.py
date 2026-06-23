"""AI Handshake guest trial quota model — privacy-minimal quota state only."""

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class AiHandshakeGuestTrialQuota(Base):
    __tablename__ = "ai_handshake_guest_trial_quotas"

    # HMAC-SHA256 hex digest (64 chars); raw install id is never stored
    install_hash = Column(String(64), primary_key=True, nullable=False)
    status = Column(String(16), nullable=False)

    # Reservation window: prevents in-flight double-spend; null when completed
    reserved_until = Column(DateTime(timezone=True), nullable=True)

    # Set when quota is permanently consumed
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('reserved', 'completed')", name="ck_aihgtq_status"),
        # Cheap index for future stale-reservation cleanup queries
        Index("idx_aihgtq_reserved_until", "reserved_until"),
    )
