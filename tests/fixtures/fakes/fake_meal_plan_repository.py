"""Fake meal plan repository for testing."""
from datetime import date
from typing import List, Optional

from src.domain.model.meal_planning import MealPlan, PlannedMeal, DailyMealPlan
from src.domain.ports.meal_plan_repository_port import MealPlanRepositoryPort


class FakeMealPlanRepository(MealPlanRepositoryPort):
    """In-memory implementation of MealPlanRepositoryPort for testing."""
    
    def __init__(self):
        self._meal_plans: dict[str, MealPlan] = {}
        self._daily_meals: dict[str, DailyMealPlan] = {}
    
    def save(self, meal_plan: MealPlan) -> MealPlan:
        """Save a meal plan."""
        self._meal_plans[meal_plan.plan_id] = meal_plan
        return meal_plan
    
    def find_by_id(self, plan_id: str) -> Optional[MealPlan]:
        """Find a meal plan by ID."""
        return self._meal_plans.get(plan_id)
    
    def find_by_user_id(self, user_id: str) -> List[MealPlan]:
        """Find meal plans for a user."""
        return [
            plan for plan in self._meal_plans.values()
            if plan.user_id == user_id
        ]
    
    def find_active_by_user_id(self, user_id: str) -> Optional[MealPlan]:
        """Find the active meal plan for a user."""
        # Return the most recent plan for simplicity
        user_plans = self.find_by_user_id(user_id)
        return user_plans[0] if user_plans else None
    
    def find_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[MealPlan]:
        """Find meal plans within a date range."""
        return [
            plan for plan in self._meal_plans.values()
            if (plan.user_id == user_id and
                any(start_date <= day.date <= end_date for day in plan.days))
        ]
    
    def delete(self, plan_id: str) -> bool:
        """Delete a meal plan."""
        if plan_id in self._meal_plans:
            del self._meal_plans[plan_id]
            return True
        return False
    
    def get_daily_meals(
        self, 
        user_id: str, 
        meal_date: date
    ) -> List[DailyMealPlan]:
        """Get daily meals for a specific date."""
        return [
            daily_meal for daily_meal in self._daily_meals.values()
            if daily_meal.user_id == user_id and daily_meal.meal_date == meal_date
        ]
    
    def save_daily_meal(self, daily_meal: DailyMealPlan) -> DailyMealPlan:
        """Save or update a daily meal."""
        key = f"{daily_meal.user_id}_{daily_meal.meal_date}"
        self._daily_meals[key] = daily_meal
        return daily_meal
    
    def get_planned_meals(
        self,
        meal_plan_id: str,
        meal_date: date
    ) -> List[PlannedMeal]:
        """Get planned meals for a specific date within a meal plan."""
        plan = self._meal_plans.get(meal_plan_id)
        if not plan:
            return []
        
        for day in plan.days:
            if day.date == meal_date:
                return day.meals
        return []
