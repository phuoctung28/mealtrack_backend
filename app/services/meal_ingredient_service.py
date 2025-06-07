from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

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
    """
    Service for managing meal ingredients and providing context for LLM recalculation.
    """
    
    def __init__(self):
        # In a real implementation, this would use a proper database
        # For now, we'll use in-memory storage
        self._ingredients: Dict[str, List[MealIngredient]] = {}
    
    def add_ingredient(self, meal_id: str, name: str, quantity: float, unit: str, 
                      calories: Optional[float] = None, macros: Optional[Dict[str, float]] = None) -> str:
        """
        Add an ingredient to a meal.
        
        Args:
            meal_id: ID of the meal
            name: Name of the ingredient
            quantity: Quantity of the ingredient
            unit: Unit of measurement
            calories: Calories per serving (optional)
            macros: Macro breakdown (optional)
            
        Returns:
            ingredient_id: Generated ID for the ingredient
        """
        import uuid
        ingredient_id = str(uuid.uuid4())
        
        ingredient = MealIngredient(
            ingredient_id=ingredient_id,
            meal_id=meal_id,
            name=name,
            quantity=quantity,
            unit=unit,
            calories=calories,
            macros=macros
        )
        
        if meal_id not in self._ingredients:
            self._ingredients[meal_id] = []
        
        self._ingredients[meal_id].append(ingredient)
        
        logger.info(f"Added ingredient {name} ({quantity} {unit}) to meal {meal_id}")
        return ingredient_id
    
    def get_ingredients_for_meal(self, meal_id: str) -> List[MealIngredient]:
        """
        Get all ingredients for a specific meal.
        
        Args:
            meal_id: ID of the meal
            
        Returns:
            List of meal ingredients
        """
        return self._ingredients.get(meal_id, [])
    
    def get_ingredients_context_for_llm(self, meal_id: str) -> List[Dict[str, Any]]:
        """
        Get ingredients formatted for LLM context.
        
        Args:
            meal_id: ID of the meal
            
        Returns:
            List of ingredient dictionaries formatted for LLM
        """
        ingredients = self.get_ingredients_for_meal(meal_id)
        
        context_ingredients = []
        for ingredient in ingredients:
            context_ingredient = {
                "name": ingredient.name,
                "quantity": ingredient.quantity,
                "unit": ingredient.unit
            }
            
            if ingredient.calories:
                context_ingredient["calories"] = ingredient.calories
            
            if ingredient.macros:
                context_ingredient["macros"] = ingredient.macros
            
            context_ingredients.append(context_ingredient)
        
        logger.info(f"Generated LLM context for {len(context_ingredients)} ingredients in meal {meal_id}")
        return context_ingredients
    
    def remove_ingredient(self, meal_id: str, ingredient_id: str) -> bool:
        """
        Remove an ingredient from a meal.
        
        Args:
            meal_id: ID of the meal
            ingredient_id: ID of the ingredient to remove
            
        Returns:
            True if ingredient was removed, False if not found
        """
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
        """
        Update an existing ingredient.
        
        Args:
            meal_id: ID of the meal
            ingredient_id: ID of the ingredient to update
            name: New name (optional)
            quantity: New quantity (optional)
            unit: New unit (optional)
            calories: New calories (optional)
            macros: New macros (optional)
            
        Returns:
            True if ingredient was updated, False if not found
        """
        if meal_id not in self._ingredients:
            return False
        
        ingredients = self._ingredients[meal_id]
        for ingredient in ingredients:
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