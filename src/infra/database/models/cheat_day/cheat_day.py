"""Cheat day database model."""

from sqlalchemy import Column, Date, DateTime, Index, String, UniqueConstraint

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin


class CheatDayORM(Base, TimestampMixin):
    __tablename__ = "cheat_days"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    date = Column(Date, nullable=False)
    marked_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_cheat_date"),
        Index("ix_user_cheat_date", "user_id", "date"),
    )
