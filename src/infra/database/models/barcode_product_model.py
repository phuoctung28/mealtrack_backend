"""
Barcode product database model for caching API responses.
"""

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, func

from src.infra.database.config import Base


class BarcodeProductModel(Base):
    """Database model for cached barcode products."""

    __tablename__ = "barcode_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    calories_100g = Column(Float)
    protein_100g = Column(Float)
    carbs_100g = Column(Float)
    fat_100g = Column(Float)
    serving_size = Column(String(100))
    image_url = Column(Text)
    source = Column(String(50), default="fatsecret")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
