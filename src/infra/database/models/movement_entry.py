"""Movement entry database model."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class MovementEntryORM(Base, BaseMixin):
    __tablename__ = "movement_entries"

    id = Column(String(64), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id = Column(String(64), nullable=True, index=True)
    activity_name = Column(String(100), nullable=False)
    duration_min = Column(Integer, nullable=False)
    kcal_burned = Column(Float, nullable=False)
    intensity = Column(String(16), nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    include_in_balance = Column(Boolean, nullable=False, default=True)
    logged_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_movement_entries_user_logged_at", "user_id", "logged_at"),
    )
