import logging
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class MealIngredient:
    """Represents an ingredient in a meal."""
    ingredient_id: str
    meal_id: str
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[Dict[str, float]] = None

class MealIngredientService:
    """Service for managing meal ingredients and LLM context."""
    
    def __init__(self):
        # In-memory storage (replace with database in production)
        self._ingredients: Dict[str, List[MealIngredient]] = {}
    
    def add_ingredient(self, meal_id: str, ingredient_data: Dict[str, Any]) -> str:
        """Add an ingredient to a meal from ingredient data dictionary."""
        ingredient_id = str(uuid.uuid4())
        
        ingredient = MealIngredient(
            ingredient_id=ingredient_id,
            meal_id=meal_id,
            name=ingredient_data.get("name", "Unknown"),
            quantity=ingredient_data.get("quantity", 0.0),
            unit=ingredient_data.get("unit", "g"),
            calories=ingredient_data.get("calories"),
            macros=ingredient_data.get("macros")
        )
        
        if meal_id not in self._ingredients:
            self._ingredients[meal_id] = []
        
        self._ingredients[meal_id].append(ingredient)
        
        logger.info(f"Added ingredient {ingredient.name} ({ingredient.quantity} {ingredient.unit}) to meal {meal_id}")
        return ingredient_id
    
    def get_ingredients_for_meal(self, meal_id: str) -> List[Dict[str, Any]]:
        """Get ingredients for meal as dictionaries for LLM context."""
        ingredients = self._ingredients.get(meal_id, [])
        
        return [
            {
                "name": ingredient.name,
                "quantity": ingredient.quantity,
                "unit": ingredient.unit,
                "calories": ingredient.calories,
                "macros": ingredient.macros
            }
            for ingredient in ingredients
        ]
    
    def remove_ingredient(self, meal_id: str, ingredient_id: str) -> bool:
        """Remove an ingredient from a meal."""
        if meal_id not in self._ingredients:
            return False
        
        ingredients = self._ingredients[meal_id]
        for i, ingredient in enumerate(ingredients):
            if ingredient.ingredient_id == ingredient_id:
                removed_ingredient = ingredients.pop(i)
                logger.info(f"Removed ingredient {removed_ingredient.name} from meal {meal_id}")
                return True
        
        return False
    
    def update_ingredient(self, meal_id: str, ingredient_id: str, 
                         name: Optional[str] = None, quantity: Optional[float] = None, 
                         unit: Optional[str] = None, calories: Optional[float] = None, 
                         macros: Optional[Dict[str, float]] = None) -> bool:
        """Update an existing ingredient."""
        if meal_id not in self._ingredients:
            return False
        
        for ingredient in self._ingredients[meal_id]:
            if ingredient.ingredient_id == ingredient_id:
                if name is not None:
                    ingredient.name = name
                if quantity is not None:
                    ingredient.quantity = quantity
                if unit is not None:
                    ingredient.unit = unit
                if calories is not None:
                    ingredient.calories = calories
                if macros is not None:
                    ingredient.macros = macros
                
                logger.info(f"Updated ingredient {ingredient.name} in meal {meal_id}")
                return True
        
        return False 