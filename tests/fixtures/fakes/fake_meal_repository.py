"""Fake meal repository for testing."""
from datetime import date
from typing import List, Optional

from src.domain.model.meal import Meal, MealStatus
from src.domain.ports.meal_repository_port import MealRepositoryPort


class FakeMealRepository(MealRepositoryPort):
    """In-memory implementation of MealRepositoryPort for testing."""
    
    def __init__(self):
        self._meals: dict[str, Meal] = {}
    
    def save(self, meal: Meal) -> Meal:
        """Save a meal to in-memory storage."""
        self._meals[meal.meal_id] = meal
        return meal
    
    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        """Find a meal by ID."""
        return self._meals.get(meal_id)
    
    def find_by_status(self, status: MealStatus, limit: int = 10) -> List[Meal]:
        """Find meals by status."""
        return [
            meal for meal in self._meals.values()
            if meal.status == status
        ][:limit]
    
    def find_all_paginated(self, offset: int = 0, limit: int = 20) -> List[Meal]:
        """Retrieve all meals with pagination."""
        meals = list(self._meals.values())
        return meals[offset:offset + limit]
    
    def count(self) -> int:
        """Count total number of meals."""
        return len(self._meals)
    
    def find_by_date(self, date_obj: date, user_id: str = None, limit: int = 50) -> List[Meal]:
        """Find meals created on a specific date."""
        meals = [
            meal for meal in self._meals.values()
            if meal.created_at.date() == date_obj
        ]
        
        if user_id:
            meals = [meal for meal in meals if meal.user_id == user_id]
        
        return meals[:limit]
    
    def delete(self, meal_id: str) -> bool:
        """Delete a meal by ID."""
        if meal_id in self._meals:
            del self._meals[meal_id]
            return True
        return False
