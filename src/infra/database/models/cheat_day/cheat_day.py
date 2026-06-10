"""Cheat day database model."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)

from src.infra.database.base import Base


class CheatDayORM(Base):
    __tablename__ = "cheat_days"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False)
    marked_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_cheat_date"),
        Index("ix_user_cheat_date", "user_id", "date"),
    )
