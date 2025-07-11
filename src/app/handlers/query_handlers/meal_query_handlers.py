"""
Query handlers for meal domain - read operations.
"""
import logging
from datetime import date
from typing import List, Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler(EventHandler[GetMealByIdQuery, Meal]):
    """Handler for retrieving a meal by ID."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository
    
    async def handle(self, query: GetMealByIdQuery) -> Meal:
        """Get meal by ID."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        meal = self.meal_repository.find_by_id(query.meal_id)
        
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {query.meal_id} not found")
        
        return meal


@handles(GetMealsByDateQuery)
class GetMealsByDateQueryHandler(EventHandler[GetMealsByDateQuery, List[Meal]]):
    """Handler for retrieving meals by date."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository
    
    async def handle(self, query: GetMealsByDateQuery) -> List[Meal]:
        """Get meals for a specific date."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        return self.meal_repository.find_by_date(query.target_date)


@handles(GetDailyMacrosQuery)
class GetDailyMacrosQueryHandler(EventHandler[GetDailyMacrosQuery, Dict[str, Any]]):
    """Handler for calculating daily macronutrient totals."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository
    
    async def handle(self, query: GetDailyMacrosQuery) -> Dict[str, Any]:
        """Calculate daily macros for a given date."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        target_date = query.target_date or date.today()
        meals = self.meal_repository.find_by_date(target_date)
        
        # Initialize totals
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        meal_count = 0
        meals_with_nutrition = 0
        
        # Calculate totals from meals with nutrition data
        for meal in meals:
            meal_count += 1
            if meal.nutrition and meal.status in [MealStatus.READY, MealStatus.ENRICHING]:
                meals_with_nutrition += 1
                total_calories += meal.nutrition.calories or 0
                if meal.nutrition.macros:
                    total_protein += meal.nutrition.macros.protein or 0
                    total_carbs += meal.nutrition.macros.carbs or 0
                    total_fat += meal.nutrition.macros.fat or 0
                    if hasattr(meal.nutrition.macros, 'fiber') and meal.nutrition.macros.fiber:
                        total_fiber += meal.nutrition.macros.fiber
        
        return {
            "date": target_date.isoformat(),
            "total_calories": round(total_calories, 1),
            "total_protein": round(total_protein, 1),
            "total_carbs": round(total_carbs, 1),
            "total_fat": round(total_fat, 1),
            "total_fiber": round(total_fiber, 1),
            "meal_count": meal_count,
            "meals_with_nutrition": meals_with_nutrition
        }


