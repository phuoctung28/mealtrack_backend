from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from src.infra.database.config import Base


class CraveSeen(Base):
    __tablename__ = "crave_seen"

    user_id = Column(String(128), primary_key=True)
    catalog_meal_id = Column(String(36), primary_key=True)
    seen_count = Column(Integer, nullable=False, default=1)
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "catalog_meal_id", name="uq_crave_seen_user_meal"),
    )
