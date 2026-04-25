"""ORM model for meal_image_cache table."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, Text, func
from sqlalchemy.dialects.postgresql import UUID

from src.infra.database.config import Base


class MealImageCacheModel(Base):
    __tablename__ = "meal_image_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_name = Column(Text, nullable=False)
    name_slug = Column(Text, nullable=False, unique=True)
    text_embedding = Column(Vector(768), nullable=False)
    image_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    source = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
