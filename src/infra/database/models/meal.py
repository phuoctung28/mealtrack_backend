import enum

from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class MealStatusEnum(enum.Enum):
    """Enum for meal status in database."""
    PROCESSING = "PROCESSING"
    ANALYZING = "ANALYZING"
    ENRICHING = "ENRICHING"
    READY = "READY"
    FAILED = "FAILED"

class Meal(Base, BaseMixin):
    """Database model for meals."""
    
    # Rename id to meal_id to match domain model
    meal_id = Column(String(36), primary_key=True)
    status = Column(Enum(MealStatusEnum), nullable=False)
    dish_name = Column(String(255), nullable=True)  # The name of the dish
    ready_at = Column(DateTime, nullable=True)  # When meal analysis was completed
    error_message = Column(Text, nullable=True)
    raw_ai_response = Column(Text, nullable=True)
    
    # Relationships
    image_id = Column(String(36), ForeignKey("mealimage.image_id"), nullable=False)
    image = relationship("MealImage", uselist=False, lazy="joined")
    nutrition = relationship("Nutrition", uselist=False, back_populates="meal", cascade="all, delete-orphan")
    
    # Override to remove the default id column from BaseMixin
    id = None
    
    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.meal import Meal as DomainMeal
        from src.domain.model.meal import MealStatus
        
        # Convert status from database enum to domain enum
        status_mapping = {
            MealStatusEnum.PROCESSING: MealStatus.PROCESSING,
            MealStatusEnum.ANALYZING: MealStatus.ANALYZING,
            MealStatusEnum.ENRICHING: MealStatus.ENRICHING,
            MealStatusEnum.READY: MealStatus.READY,
            MealStatusEnum.FAILED: MealStatus.FAILED,
        }
        
        return DomainMeal(
            meal_id=self.meal_id,
            status=status_mapping[self.status],
            created_at=self.created_at,
            image=self.image.to_domain() if self.image else None,
            dish_name=self.dish_name,
            nutrition=self.nutrition.to_domain() if self.nutrition else None,
            ready_at=self.ready_at,  # Include ready_at timestamp
            error_message=self.error_message,
            raw_gpt_json=self.raw_ai_response
        )
    
    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from src.domain model."""
        from src.domain.model.meal import MealStatus
        
        # Convert status from src.domain enum to database enum
        status_mapping = {
            MealStatus.PROCESSING: MealStatusEnum.PROCESSING,
            MealStatus.ANALYZING: MealStatusEnum.ANALYZING,
            MealStatus.ENRICHING: MealStatusEnum.ENRICHING,
            MealStatus.READY: MealStatusEnum.READY,
            MealStatus.FAILED: MealStatusEnum.FAILED,
        }
        
        # Create meal
        meal = cls(
            meal_id=domain_model.meal_id,
            status=status_mapping[domain_model.status],
            created_at=domain_model.created_at,
            updated_at=getattr(domain_model, "updated_at", None),
            dish_name=getattr(domain_model, "dish_name", None),
            ready_at=getattr(domain_model, "ready_at", None),  # Include ready_at timestamp
            error_message=getattr(domain_model, "error_message", None),
            raw_ai_response=getattr(domain_model, "raw_gpt_json", None),
        )
        
        # Add image reference
        if domain_model.image:
            meal.image_id = domain_model.image.image_id
            
        # Add nutrition if it exists
        if domain_model.nutrition:
            from src.infra.database.models.nutrition import Nutrition
            meal.nutrition = Nutrition.from_domain(domain_model.nutrition, meal_id=domain_model.meal_id)
            
        return meal 