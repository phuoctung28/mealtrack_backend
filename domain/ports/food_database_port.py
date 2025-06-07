from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from domain.model.nutrition import FoodItem

class FoodDatabasePort(ABC):
    """Port interface for food database lookup services."""
    
    @abstractmethod
    def lookup(self, food_name: str, quantity: float, unit: str) -> Optional[FoodItem]:
        """
        Looks up nutritional information for a food item.
        
        Args:
            food_name: Name of the food
            quantity: Quantity of the food
            unit: Unit of measurement (e.g., "g", "oz", "serving")
            
        Returns:
            FoodItem with standardized nutritional data if found, None otherwise
        """
        pass
    
    @abstractmethod
    def lookup_batch(self, food_items: list[Dict[str, Any]]) -> Dict[str, Optional[FoodItem]]:
        """
        Looks up nutritional information for multiple food items.
        
        Args:
            food_items: List of dictionaries with food name, quantity, and unit
            
        Returns:
            Dictionary mapping food names to FoodItems (or None if not found)
        """
        pass 