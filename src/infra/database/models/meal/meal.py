"""
Meal model for the main meal entity.
"""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Integer, Boolean
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin
from src.infra.database.models.enums import MealStatusEnum


class Meal(Base, TimestampMixin):
    """Database model for meals."""
    
    __tablename__ = 'meal'
    
    # Primary key
    meal_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)  # User who created this meal
    status = Column(Enum(MealStatusEnum), nullable=False)
    dish_name = Column(String(255), nullable=True)  # The name of the dish
    ready_at = Column(DateTime, nullable=True)  # When meal analysis was completed
    error_message = Column(Text, nullable=True)
    raw_ai_response = Column(Text, nullable=True)
    
    # Edit tracking fields
    last_edited_at = Column(DateTime, nullable=True)  # When meal was last edited
    edit_count = Column(Integer, default=0, nullable=False)  # Number of times edited
    is_manually_edited = Column(Boolean, default=False, nullable=False)  # Whether meal has been manually edited
    
    # Relationships
    image_id = Column(String(36), ForeignKey("mealimage.image_id"), nullable=False)
    image = relationship("MealImage", uselist=False, lazy="joined")
    nutrition = relationship("Nutrition", uselist=False, back_populates="meal", cascade="all, delete-orphan")
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.meal import Meal as DomainMeal
        from src.infra.mappers import MealStatusMapper

        return DomainMeal(
            meal_id=self.meal_id,
            user_id=self.user_id,
            status=MealStatusMapper.to_domain(self.status),
            created_at=self.created_at,
            image=self.image.to_domain() if self.image else None,
            dish_name=self.dish_name,
            nutrition=self.nutrition.to_domain() if self.nutrition else None,
            ready_at=self.ready_at,
            error_message=self.error_message,
            raw_gpt_json=self.raw_ai_response,
            updated_at=self.updated_at,
            last_edited_at=self.last_edited_at,
            edit_count=self.edit_count,
            is_manually_edited=self.is_manually_edited
        )
    
    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from domain model."""
        from datetime import datetime
        from src.infra.mappers import MealStatusMapper

        # Create meal
        meal = cls(
            meal_id=domain_model.meal_id,
            user_id=getattr(domain_model, "user_id", None),
            status=MealStatusMapper.to_db(domain_model.status),
            created_at=domain_model.created_at,
            updated_at=getattr(domain_model, "updated_at", None) or datetime.now(),
            dish_name=getattr(domain_model, "dish_name", None),
            ready_at=getattr(domain_model, "ready_at", None),
            error_message=getattr(domain_model, "error_message", None),
            raw_ai_response=getattr(domain_model, "raw_gpt_json", None),
            last_edited_at=getattr(domain_model, "last_edited_at", None),
            edit_count=getattr(domain_model, "edit_count", 0),
            is_manually_edited=getattr(domain_model, "is_manually_edited", False)
        )

        # Add image reference
        if domain_model.image:
            meal.image_id = domain_model.image.image_id

        # Add nutrition if it exists
        if domain_model.nutrition:
            from src.infra.database.models.nutrition.nutrition import Nutrition
            meal.nutrition = Nutrition.from_domain(domain_model.nutrition, meal_id=domain_model.meal_id)

        return meal