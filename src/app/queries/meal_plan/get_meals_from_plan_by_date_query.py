"""
GetMealsFromPlanByDateQuery - Query for retrieving planned meals by date.
This is distinct from GetMealsByDateQuery which retrieves actual meals.
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class GetMealsFromPlanByDateQuery:
    """Query to get meals from a meal plan for a specific date."""
    user_id: str
    meal_date: date