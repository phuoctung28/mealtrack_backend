from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.model.meal import Meal, MealStatus


class MealRepositoryPort(ABC):
    """Port interface for meal persistence operations."""
    
    @abstractmethod
    def save(self, meal: Meal) -> Meal:
        """
        Persists a meal entity.
        
        Args:
            meal: The meal to be saved
            
        Returns:
            The saved meal with any generated IDs
        """
        pass
    
    @abstractmethod
    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        """
        Finds a meal by its ID.
        
        Args:
            meal_id: The ID of the meal to find
            
        Returns:
            The meal if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_status(self, status: MealStatus, limit: int = 10) -> List[Meal]:
        """
        Finds meals by status.
        
        Args:
            status: The status to filter by
            limit: Maximum number of results
            
        Returns:
            List of meals with the specified status
        """
        pass
    
    @abstractmethod
    def find_all_paginated(self, offset: int = 0, limit: int = 20) -> List[Meal]:
        """
        Retrieves all meals with pagination.
        
        Args:
            offset: Pagination offset
            limit: Maximum number of results
            
        Returns:
            Paginated list of meals
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Counts the total number of meals.
        
        Returns:
            Total count
        """
        pass
    
    @abstractmethod
    def find_by_date(self, date, user_id: str = None, limit: int = 50) -> List[Meal]:
        """
        Finds meals created on a specific date, optionally filtered by user.
        
        Args:
            date: The date to filter by (date object)
            user_id: Optional user ID to filter meals by specific user
            limit: Maximum number of results
            
        Returns:
            List of meals created on the specified date
        """
        pass 