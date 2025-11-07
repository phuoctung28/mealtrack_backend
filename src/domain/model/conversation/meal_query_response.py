"""
Domain models for meal query responses.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any

from ..meal_planning import PlannedMeal


@dataclass
class MealsForDateResponse:
    """Response model for getting meals by date query."""
    
    date: date
    day_formatted: str
    meals: List[PlannedMeal]
    total_meals: int
    user_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "date": self.date.isoformat(),
            "day_formatted": self.day_formatted,
            "meals": [meal.to_dict() for meal in self.meals],
            "total_meals": self.total_meals,
            "user_id": self.user_id
        }
    
    @classmethod
    def empty_response(cls, user_id: str, query_date: date) -> 'MealsForDateResponse':
        """Create an empty response for when no meals are found."""
        return cls(
            date=query_date,
            day_formatted=query_date.strftime("%A, %B %d, %Y"),
            meals=[],
            total_meals=0,
            user_id=user_id
        )