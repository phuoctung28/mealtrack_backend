"""ORM model for the pending-resolution queue."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, Text, func

from src.infra.database.config import Base


class PendingMealImageResolutionModel(Base):
    __tablename__ = "pending_meal_image_resolution"

    name_slug = Column(Text, primary_key=True)
    meal_name = Column(Text, nullable=False)
    candidate_image_url = Column(Text, nullable=True)
    candidate_thumbnail_url = Column(Text, nullable=True)
    candidate_source = Column(Text, nullable=True)
    enqueued_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attempts = Column(Integer, nullable=False, server_default="0")
    last_error = Column(Text, nullable=True)
