import uuid
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Dict, Any

from src.domain.utils.timezone_utils import utc_now
from ..nutrition import Macros


@dataclass
class UserMacros:
    """
    Domain model representing daily macro targets and consumption for a user.
    """
    user_macros_id: str
    user_id: Optional[str]  # For when user system is implemented
    target_date: date
    target_calories: float
    target_macros: Macros
    consumed_calories: float = 0.0
    consumed_macros: Optional[Macros] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    onboard_data: Optional[Dict[str, Any]] = None  # Store onboarding choices
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID format
        try:
            uuid.UUID(self.user_macros_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_macros_id: {self.user_macros_id}")
        
        if self.user_id:
            try:
                uuid.UUID(self.user_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        if self.target_calories <= 0:
            raise ValueError(f"Target calories must be positive: {self.target_calories}")
            
        if self.consumed_calories < 0:
            raise ValueError(f"Consumed calories cannot be negative: {self.consumed_calories}")
        
        # Initialize consumed macros if not provided
        if self.consumed_macros is None:
            object.__setattr__(self, 'consumed_macros', Macros(protein=0.0, carbs=0.0, fat=0.0))
    
    @classmethod
    def create_new(cls, target_date: date, target_calories: float, target_macros: Macros, **kwargs) -> 'UserMacros':
        """Factory method to create new user macros."""
        return cls(
            user_macros_id=str(uuid.uuid4()),
            target_date=target_date,
            target_calories=target_calories,
            target_macros=target_macros,
            created_at=utc_now(),
            **kwargs
        )
    
    @classmethod
    def create_from_onboarding(cls, target_date: date, target_calories: float, target_macros: Macros, onboard_data: Dict[str, Any]) -> 'UserMacros':
        """Create user macros from onboarding data."""
        return cls.create_new(
            target_date=target_date,
            target_calories=target_calories,
            target_macros=target_macros,
            onboard_data=onboard_data
        )
    
    def add_consumed_nutrition(self, calories: float, macros: Macros) -> 'UserMacros':
        """Add consumed nutrition to daily totals."""
        new_consumed_calories = self.consumed_calories + calories
        new_consumed_macros = Macros(
            protein=self.consumed_macros.protein + macros.protein,
            carbs=self.consumed_macros.carbs + macros.carbs,
            fat=self.consumed_macros.fat + macros.fat,
        )

        return UserMacros(
            user_macros_id=self.user_macros_id,
            user_id=self.user_id,
            target_date=self.target_date,
            target_calories=self.target_calories,
            target_macros=self.target_macros,
            consumed_calories=new_consumed_calories,
            consumed_macros=new_consumed_macros,
            created_at=self.created_at,
            updated_at=utc_now(),
            onboard_data=self.onboard_data
        )
    
    @property
    def remaining_calories(self) -> float:
        """Calculate remaining calories for the day."""
        return max(0, self.target_calories - self.consumed_calories)
    
    @property
    def remaining_macros(self) -> Macros:
        """Calculate remaining macros for the day."""
        return Macros(
            protein=max(0, self.target_macros.protein - self.consumed_macros.protein),
            carbs=max(0, self.target_macros.carbs - self.consumed_macros.carbs),
            fat=max(0, self.target_macros.fat - self.consumed_macros.fat),
        )
    
    @property
    def completion_percentage(self) -> Dict[str, float]:
        """Calculate completion percentage for calories and macros."""
        return {
            "calories": min(100.0, (self.consumed_calories / self.target_calories) * 100),
            "protein": min(100.0, (self.consumed_macros.protein / self.target_macros.protein) * 100),
            "carbs": min(100.0, (self.consumed_macros.carbs / self.target_macros.carbs) * 100),
            "fat": min(100.0, (self.consumed_macros.fat / self.target_macros.fat) * 100)
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "user_macros_id": self.user_macros_id,
            "target_date": self.target_date.isoformat(),
            "target_calories": self.target_calories,
            "target_macros": self.target_macros.to_dict(),
            "consumed_calories": self.consumed_calories,
            "consumed_macros": self.consumed_macros.to_dict(),
            "remaining_calories": self.remaining_calories,
            "remaining_macros": self.remaining_macros.to_dict(),
            "completion_percentage": self.completion_percentage
        }
        
        if self.user_id:
            result["user_id"] = self.user_id
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        if self.onboard_data:
            result["onboard_data"] = self.onboard_data
            
        return result 