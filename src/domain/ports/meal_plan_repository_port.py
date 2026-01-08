"""
MealPlanRepositoryPort - Interface for meal plan repository operations.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List

from src.domain.model.meal_planning import MealPlan, PlannedMeal, DailyMealPlan


class MealPlanRepositoryPort(ABC):
    """Interface for meal plan repository operations."""
    
    @abstractmethod
    def save(self, meal_plan: MealPlan) -> MealPlan:
        """Save or update a meal plan."""
        pass
    
    @abstractmethod
    def find_by_id(self, meal_plan_id: str) -> Optional[MealPlan]:
        """Find a meal plan by ID."""
        pass
    
    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[MealPlan]:
        """Find all meal plans for a user."""
        pass
    
    @abstractmethod
    def find_active_by_user_id(self, user_id: str) -> Optional[MealPlan]:
        """Find the active meal plan for a user."""
        pass
    
    @abstractmethod
    def find_by_date_range(
        self, 
        user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[MealPlan]:
        """Find meal plans within a date range."""
        pass
    
    @abstractmethod
    def delete(self, meal_plan_id: str) -> bool:
        """Delete a meal plan by ID."""
        pass
    
    @abstractmethod
    def get_daily_meals(
        self, 
        user_id: str, 
        meal_date: date
    ) -> List[DailyMealPlan]:
        """Get daily meals for a specific date."""
        pass
    
    @abstractmethod
    def save_daily_meal(self, daily_meal: DailyMealPlan) -> DailyMealPlan:
        """Save or update a daily meal."""
        pass
    
    @abstractmethod
    def get_planned_meals(
        self,
        meal_plan_id: str,
        meal_date: date
    ) -> List[PlannedMeal]:
        """Get planned meals for a specific date within a meal plan."""
        pass