from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String

from src.infra.database.config import Base


class CraveSwipeEvent(Base):
    __tablename__ = "crave_swipe_events"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(128), nullable=False)
    catalog_meal_id = Column(String(36), nullable=False)
    deck_id = Column(String(36), nullable=True)
    direction = Column(String(8), nullable=False)
    position = Column(Integer, nullable=True)
    dwell_ms = Column(Integer, nullable=True)
    meal_type = Column(String(20), nullable=True)
    context = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_crave_swipe_user_created", "user_id", "created_at"),
        Index("ix_crave_swipe_meal", "catalog_meal_id"),
    )
