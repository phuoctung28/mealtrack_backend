"""Weight entry database model."""

from sqlalchemy import Column, String, Float, DateTime, UniqueConstraint, Index, ForeignKey
from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class WeightEntryORM(Base, BaseMixin):
    """Stores user weight history for progress tracking."""

    __tablename__ = "weight_entries"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weight_kg = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "recorded_at", name="uq_user_recorded_at"),
        Index("idx_weight_entries_user_recorded", "user_id", "recorded_at"),
    )
