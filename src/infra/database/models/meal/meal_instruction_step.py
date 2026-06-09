"""Normalized recipe instruction rows for meals."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class MealInstructionStepORM(Base):
    """Ordered recipe instruction for a meal."""

    __tablename__ = "meal_instruction_steps"

    id = Column(String(36), primary_key=True)
    meal_id = Column(
        String(36),
        ForeignKey("meal.meal_id", ondelete="CASCADE"),
        nullable=False,
    )
    instruction = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    position = Column(Integer, nullable=False)

    meal = relationship("MealORM", back_populates="instruction_steps")

    __table_args__ = (
        Index("idx_meal_instruction_steps_meal_position", "meal_id", "position"),
    )
