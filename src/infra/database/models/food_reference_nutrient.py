"""Normalized extended nutrient rows for canonical foods."""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base


class FoodReferenceNutrientModel(Base):
    """Queryable non-macro nutrient for a food reference."""

    __tablename__ = "food_reference_nutrients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_reference_id = Column(
        Integer,
        ForeignKey("food_reference.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrient_key = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    unit = Column(String(32), nullable=True)

    food_reference = relationship("FoodReferenceModel", back_populates="nutrient_rows")

    __table_args__ = (
        UniqueConstraint(
            "food_reference_id",
            "nutrient_key",
            name="uq_food_reference_nutrient_key",
        ),
        Index(
            "idx_food_reference_nutrients_ref_key",
            "food_reference_id",
            "nutrient_key",
        ),
    )
