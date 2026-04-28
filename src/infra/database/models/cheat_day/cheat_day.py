"""Cheat day database model."""

from sqlalchemy import Column, String, Date, DateTime, UniqueConstraint, Index
from src.infra.database.config import Base


class CheatDayORM(Base):
    __tablename__ = "cheat_days"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    date = Column(Date, nullable=False)
    marked_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_cheat_date"),
        Index("ix_user_cheat_date", "user_id", "date"),
    )
