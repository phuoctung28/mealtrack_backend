"""
Food reference database model — canonical food catalog.
Evolved from barcode_products to serve as the single source of truth
for per-100g nutrition data across barcode scans, USDA, and FatSecret.
"""
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, String, Text, func,
)

from src.infra.database.config import Base


class FoodReferenceModel(Base):
    """Database model for canonical food reference entries."""

    __tablename__ = "food_reference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode = Column(String(20), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    name_normalized = Column(String(255), nullable=True, index=True)
    name_vi = Column(String(255), nullable=True)
    brand = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    region = Column(String(10), nullable=False, default="global")
    fdc_id = Column(Integer, nullable=True, index=True)

    # Nutrition per 100g — calories always derived from macros
    protein_100g = Column(Float, nullable=True)
    carbs_100g = Column(Float, nullable=True)
    fat_100g = Column(Float, nullable=True)
    fiber_100g = Column(Float, nullable=False, default=0)
    sugar_100g = Column(Float, nullable=False, default=0)

    # Extended nutrients (calcium_mg, iron_mg, vitamin_a_mcg, etc.)
    extra_nutrients = Column(JSON, nullable=True)

    # Conversion data
    serving_sizes = Column(JSON, nullable=True)  # [{name, grams}, ...]
    density = Column(Float, nullable=False, default=1.0)  # g/ml
    serving_size = Column(String(100), nullable=True)  # legacy text

    # Metadata
    source = Column(String(50), nullable=False, default="fatsecret")
    is_verified = Column(Boolean, nullable=False, default=False)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
