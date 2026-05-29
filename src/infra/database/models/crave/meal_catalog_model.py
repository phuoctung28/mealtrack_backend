from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from src.infra.database.config import Base


class MealCatalog(Base):
    __tablename__ = "meal_catalog"

    id = Column(String(36), primary_key=True)
    meal_name = Column(String(255), nullable=False)
    english_name = Column(String(255), nullable=False)

    calories = Column(Integer, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, nullable=False, default=0.0)
    calorie_band = Column(Integer, nullable=False)

    cuisine = Column(String(64), nullable=True)
    meal_types = Column(JSON, nullable=False, default=list)
    ingredients = Column(JSON, nullable=False, default=list)
    recipe_steps = Column(JSON, nullable=True)
    recipe_status = Column(String(16), nullable=False, default="none")
    prep_time_minutes = Column(Integer, nullable=True)

    dietary_flags = Column(JSON, nullable=False, default=list)
    allergen_flags = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)

    image_url = Column(String(1024), nullable=True)
    thumbnail_url = Column(String(1024), nullable=True)
    image_status = Column(String(16), nullable=False, default="pending")

    embedding = Column(Vector(512), nullable=True)

    times_shown = Column(Integer, nullable=False, default=0)
    times_saved = Column(Integer, nullable=False, default=0)
    times_cooked = Column(Integer, nullable=False, default=0)
    times_skipped = Column(Integer, nullable=False, default=0)

    origin = Column(String(24), nullable=False, default="generated")
    status = Column(String(16), nullable=False, default="active")
    language = Column(String(8), nullable=False, default="en")

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
