import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MealAnalysisStrategy(ABC):
    """Abstract base class for meal analysis strategies using Strategy pattern."""
    
    @abstractmethod
    def get_analysis_prompt(self) -> str:
        """Get the system prompt for this analysis strategy."""
        pass
    
    @abstractmethod
    def get_user_message(self) -> str:
        """Get the user message for this analysis strategy."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy for logging."""
        pass

class BasicAnalysisStrategy(MealAnalysisStrategy):
    """Basic meal analysis without additional context."""
    
    def get_analysis_prompt(self) -> str:
        return """You are a nutrition analysis assistant that can analyze food in images.
        Examine the image carefully and provide detailed nutritional information.
        
        Return your analysis in the following JSON format:
        {
          "foods": [
            {
              "name": "Food name",
              "quantity": 1.0,
              "unit": "serving/g/oz/cup/etc",
              "calories": 100,
              "macros": {
                "protein": 10,
                "carbs": 20,
                "fat": 5,
                "fiber": 2
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.8
        }
        
        Requirements:
        - Each food item should include name, estimated quantity, unit, calories, and macros
        - All macros should be in grams
        - Confidence should be between 0 (low) and 1 (high)
        - Always return well-formed JSON"""
    
    def get_user_message(self) -> str:
        return "Analyze this food image and provide nutritional information:"
    
    def get_strategy_name(self) -> str:
        return "BasicAnalysis"

class PortionAwareAnalysisStrategy(MealAnalysisStrategy):
    """Portion-aware meal analysis strategy."""
    
    def __init__(self, portion_size: float, unit: str):
        self.portion_size = portion_size
        self.unit = unit
        logger.info(f"Created PortionAwareAnalysisStrategy: {portion_size} {unit}")
    
    def get_analysis_prompt(self) -> str:
        return """You are a nutrition analysis assistant that can analyze food in images with portion awareness.
        The user has specified a target portion size. Please adjust your calculations accordingly.
        
        Return your analysis in the following JSON format:
        {
          "foods": [
            {
              "name": "Food name",
              "quantity": 1.0,
              "unit": "serving/g/oz/cup/etc",
              "calories": 100,
              "macros": {
                "protein": 10,
                "carbs": 20,
                "fat": 5,
                "fiber": 2
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.8,
          "portion_adjustment": "Adjusted for specified portion size"
        }
        
        Requirements:
        - Each food item should reflect the specified portion size
        - Calculate nutrition values proportionally to match the target portion
        - All macros should be in grams
        - Include portion_adjustment field to indicate scaling was applied
        - Always return well-formed JSON"""
    
    def get_user_message(self) -> str:
        return f"""Analyze this food image and provide nutritional information.

PORTION CONTEXT: The user specified this portion should be approximately {self.portion_size} {self.unit}. 
Please adjust your nutritional calculations to match this target portion size.

Consider the visual portion size in the image and scale the nutrition values to match the specified {self.portion_size} {self.unit}."""
    
    def get_strategy_name(self) -> str:
        return f"PortionAware({self.portion_size}{self.unit})"

class IngredientAwareAnalysisStrategy(MealAnalysisStrategy):
    """Ingredient-aware meal analysis strategy."""
    
    def __init__(self, ingredients: List[Dict[str, Any]]):
        self.ingredients = ingredients
        logger.info(f"Created IngredientAwareAnalysisStrategy with {len(ingredients)} ingredients")
    
    def get_analysis_prompt(self) -> str:
        return """You are a nutrition analysis assistant that can analyze food in images with ingredient awareness.
        The user has provided a list of ingredients in this meal. Use this information to enhance your analysis.
        
        Return your analysis in the following JSON format:
        {
          "foods": [
            {
              "name": "Food name",
              "quantity": 1.0,
              "unit": "serving/g/oz/cup/etc",  
              "calories": 100,
              "macros": {
                "protein": 10,
                "carbs": 20,
                "fat": 5,
                "fiber": 2
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.9,
          "ingredient_based": true,
          "combined_nutrition": "Calculated based on provided ingredients"
        }
        
        Requirements:
        - Use the provided ingredient list to improve accuracy
        - Calculate total nutrition considering all ingredients combined
        - Account for cooking methods and ingredient interactions
        - Higher confidence scores are appropriate when ingredients are known
        - Include ingredient_based field to indicate enhanced analysis
        - Always return well-formed JSON"""
    
    def get_user_message(self) -> str:
        ingredient_lines = []
        for ing in self.ingredients:
            line = f"- {ing['name']}: {ing['quantity']} {ing['unit']}"
            if ing.get('calories'):
                line += f" ({ing['calories']} calories)"
            if ing.get('macros'):
                macros = ing['macros']
                line += f" [P:{macros.get('protein', 0)}g, C:{macros.get('carbs', 0)}g, F:{macros.get('fat', 0)}g]"
            ingredient_lines.append(line)
        
        ingredients_text = "\n".join(ingredient_lines)
        
        return f"""Analyze this food image and provide nutritional information.

INGREDIENT CONTEXT: The user has provided the following ingredients for this meal:
{ingredients_text}

Please use this ingredient information to provide a more accurate nutritional analysis. Consider how these ingredients combine and interact in the prepared dish shown in the image."""
    
    def get_strategy_name(self) -> str:
        return f"IngredientAware({len(self.ingredients)}ingredients)"

class AnalysisStrategyFactory:
    """Factory for creating analysis strategies."""
    
    @staticmethod
    def create_basic_strategy() -> MealAnalysisStrategy:
        return BasicAnalysisStrategy()
    
    @staticmethod
    def create_portion_strategy(portion_size: float, unit: str) -> MealAnalysisStrategy:
        return PortionAwareAnalysisStrategy(portion_size, unit)
    
    @staticmethod
    def create_ingredient_strategy(ingredients: List[Dict[str, Any]]) -> MealAnalysisStrategy:
        return IngredientAwareAnalysisStrategy(ingredients)
    
    @staticmethod
    def create_combined_strategy(
        portion_size: Optional[float] = None, 
        unit: Optional[str] = None,
        ingredients: Optional[List[Dict[str, Any]]] = None
    ) -> MealAnalysisStrategy:
        """Create combined strategy with both portion and ingredient awareness."""
        if ingredients and portion_size and unit:
            # For now, prioritize ingredient awareness when both are provided
            return AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
        elif ingredients:
            return AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
        elif portion_size and unit:
            return AnalysisStrategyFactory.create_portion_strategy(portion_size, unit)
        else:
            return AnalysisStrategyFactory.create_basic_strategy() 