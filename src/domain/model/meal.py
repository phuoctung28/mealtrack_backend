import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .meal_image import MealImage
from .nutrition import Nutrition


class MealStatus(Enum):
    """Status of a meal in the analysis pipeline."""
    PROCESSING = "PROCESSING"  # Initial state, waiting for analysis
    ANALYZING = "ANALYZING"    # AI analysis in progress
    ENRICHING = "ENRICHING"    # Enrichment with food database in progress
    READY = "READY"            # Final state, analysis complete
    FAILED = "FAILED"          # Analysis failed
    
    def __str__(self):
        return self.value

@dataclass
class Meal:
    """
    Aggregate root representing a meal with its image and nutritional information.
    This is the main entity in the domain.
    """
    meal_id: str  # UUID as string
    status: MealStatus
    created_at: datetime
    image: MealImage
    dish_name: Optional[str] = None
    nutrition: Optional[Nutrition] = None
    ready_at: Optional[datetime] = None
    error_message: Optional[str] = None
    raw_gpt_json: Optional[str] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID format
        try:
            uuid.UUID(self.meal_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for meal_id: {self.meal_id}")
        
        # Status-based validations
        if self.status == MealStatus.READY and self.nutrition is None:
            raise ValueError("Meal with READY status must have nutrition data")
            
        if self.status == MealStatus.READY and self.ready_at is None:
            raise ValueError("Meal with READY status must have ready_at timestamp")
            
        if self.status == MealStatus.FAILED and self.error_message is None:
            raise ValueError("Meal with FAILED status must have error_message")
    
    @classmethod
    def create_new_processing(cls, image: MealImage) -> 'Meal':
        """Factory method to create a new meal in PROCESSING status."""
        return cls(
            meal_id=str(uuid.uuid4()),
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=image
        )
    
    def mark_analyzing(self) -> 'Meal':
        """Transition to ANALYZING state."""
        return Meal(
            meal_id=self.meal_id,
            status=MealStatus.ANALYZING,
            created_at=self.created_at,
            image=self.image,
            dish_name=self.dish_name,
            nutrition=self.nutrition,
            ready_at=self.ready_at,
            error_message=self.error_message,
            raw_gpt_json=self.raw_gpt_json
        )
    
    def mark_enriching(self, raw_gpt_json: str) -> 'Meal':
        """Transition to ENRICHING state with GPT response."""
        return Meal(
            meal_id=self.meal_id,
            status=MealStatus.ENRICHING,
            created_at=self.created_at,
            image=self.image,
            dish_name=self.dish_name,
            nutrition=self.nutrition,
            ready_at=self.ready_at,
            error_message=self.error_message,
            raw_gpt_json=raw_gpt_json
        )
    
    def mark_ready(self, nutrition: Nutrition, dish_name: str) -> 'Meal':
        """Transition to READY state with final nutrition data."""
        return Meal(
            meal_id=self.meal_id,
            status=MealStatus.READY,
            created_at=self.created_at,
            image=self.image,
            dish_name=dish_name,
            nutrition=nutrition,
            ready_at=datetime.now(),
            error_message=self.error_message,
            raw_gpt_json=self.raw_gpt_json
        )
    
    def mark_failed(self, error_message: str) -> 'Meal':
        """Transition to FAILED state with error message."""
        return Meal(
            meal_id=self.meal_id,
            status=MealStatus.FAILED,
            created_at=self.created_at,
            image=self.image,
            dish_name=self.dish_name,
            nutrition=self.nutrition,
            ready_at=self.ready_at,
            error_message=error_message,
            raw_gpt_json=self.raw_gpt_json
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "meal_id": self.meal_id,
            "status": str(self.status),
            "created_at": self.created_at.isoformat(),
            "image": self.image.to_dict()
        }
        
        if self.dish_name is not None:
            result["dish_name"] = self.dish_name
            
        if self.nutrition is not None:
            result["nutrition"] = self.nutrition.to_dict()
            
        if self.ready_at is not None:
            result["ready_at"] = self.ready_at.isoformat()
            
        if self.error_message is not None:
            result["error_message"] = self.error_message
        
        return result 