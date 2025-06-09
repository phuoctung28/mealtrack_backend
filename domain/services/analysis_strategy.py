from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MealAnalysisStrategy(ABC):
    """
    Abstract base class for meal analysis strategies.
    
    This implements the Strategy pattern for different types of context-aware
    meal analysis (basic, portion-aware, ingredient-aware, etc.)
    """
    
    @abstractmethod
    def get_analysis_prompt(self) -> str:
        """
        Get the system prompt for this analysis strategy.
        
        Returns:
            str: The system prompt text
        """
        pass
    
    @abstractmethod
    def get_user_message(self) -> str:
        """
        Get the user message for this analysis strategy.
        
        Returns:
            str: The user message text with context
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of this strategy for logging.
        
        Returns:
            str: Strategy name
        """
        pass

class BasicAnalysisStrategy(MealAnalysisStrategy):
    """
    Basic meal analysis strategy without additional context.
    """
    
    def get_analysis_prompt(self) -> str:
        return """
        You are a nutrition analysis assistant that can analyze food in images.
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
        
        - Each food item should include name, estimated quantity, unit of measurement, calories, and macros
        - For quantities, estimate as precisely as possible based on visual cues
        - All macros should be in grams
        - Confidence should be between 0 (low) and 1 (high) based on how certain you are of your analysis
        - Always return well-formed JSON
        """
    
    def get_user_message(self) -> str:
        return "Analyze this food image and provide nutritional information:"
    
    def get_strategy_name(self) -> str:
        return "BasicAnalysis"

class PortionAwareAnalysisStrategy(MealAnalysisStrategy):
    """
    Portion-aware meal analysis strategy.
    """
    
    def __init__(self, portion_size: float, unit: str):
        self.portion_size = portion_size
        self.unit = unit
        logger.info(f"Created PortionAwareAnalysisStrategy: {portion_size} {unit}")
    
    def get_analysis_prompt(self) -> str:
        return """
        You are a nutrition analysis assistant that can analyze food in images with portion awareness.
        Examine the image carefully and provide detailed nutritional information adjusted for the specified portion size.
        
        IMPORTANT: The user has specified a target portion size. Please adjust your calculations accordingly.
        
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
        
        - Each food item should reflect the specified portion size
        - Calculate nutrition values proportionally to match the target portion
        - All macros should be in grams
        - Confidence should be between 0 (low) and 1 (high)
        - Include portion_adjustment field to indicate scaling was applied
        - Always return well-formed JSON
        """
    
    def get_user_message(self) -> str:
        return f"""Analyze this food image and provide nutritional information.

PORTION CONTEXT: The user has specified that this portion should be approximately {self.portion_size} {self.unit}. 
Please adjust your nutritional calculations accordingly to match this target portion size.

Consider the visual portion size in the image and scale the nutrition values to match the specified {self.portion_size} {self.unit}."""
    
    def get_strategy_name(self) -> str:
        return f"PortionAware({self.portion_size}{self.unit})"

class IngredientAwareAnalysisStrategy(MealAnalysisStrategy):
    """
    Ingredient-aware meal analysis strategy.
    """
    
    def __init__(self, ingredients: List[Dict[str, Any]]):
        self.ingredients = ingredients
        logger.info(f"Created IngredientAwareAnalysisStrategy with {len(ingredients)} ingredients")
    
    def get_analysis_prompt(self) -> str:
        return """
        You are a nutrition analysis assistant that can analyze food in images with ingredient awareness.
        Examine the image carefully and provide detailed nutritional information considering the known ingredients.
        
        IMPORTANT: The user has provided a list of ingredients in this meal. Please use this information to enhance your analysis.
        
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
        
        - Use the provided ingredient list to improve accuracy
        - Calculate total nutrition considering all ingredients combined
        - Account for cooking methods and ingredient interactions
        - Higher confidence scores are appropriate when ingredients are known
        - Include ingredient_based field to indicate enhanced analysis
        - Always return well-formed JSON
        """
    
    def get_user_message(self) -> str:
        # Format ingredients list
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

INGREDIENT CONTEXT: The user has specified that this meal contains the following ingredients:
{ingredients_text}

Please calculate the total nutritional content considering all these ingredients together. 
Use this ingredient information to enhance the accuracy of your analysis and provide more precise nutrition calculations.
Account for how these ingredients combine and any cooking methods that might affect the nutritional values."""
    
    def get_strategy_name(self) -> str:
        return f"IngredientAware({len(self.ingredients)}ingredients)"

class WeightAwareAnalysisStrategy(MealAnalysisStrategy):
    """
    Weight-aware meal analysis strategy.
    """
    
    def __init__(self, weight_grams: float):
        self.weight_grams = weight_grams
        logger.info(f"Created WeightAwareAnalysisStrategy: {weight_grams}g")
    
    def get_analysis_prompt(self) -> str:
        return """
        You are a nutrition analysis assistant that can analyze food in images with weight awareness.
        Examine the image carefully and provide detailed nutritional information adjusted for the specified total weight.
        
        IMPORTANT: The user has specified a target total weight for this meal. Please adjust your calculations accordingly.
        
        Return your analysis in the following JSON format:
        {
          "foods": [
            {
              "name": "Food name",
              "quantity": 1.0,
              "unit": "g",
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
          "confidence": 0.85,
          "weight_adjustment": "Adjusted for specified total weight",
          "total_weight_grams": 300
        }
        
        - Each food item should reflect proportions that add up to the target total weight
        - Calculate nutrition values to match the specified total weight
        - Use grams as the primary unit for quantities
        - All macros should be in grams
        - Higher confidence scores are appropriate with weight context
        - Include weight_adjustment and total_weight_grams fields
        - Always return well-formed JSON
        """
    
    def get_user_message(self) -> str:
        return f"""Analyze this food image and provide nutritional information.

WEIGHT CONTEXT: The user has specified that this meal should have a total weight of {self.weight_grams} grams.

Please examine the visual portions in the image and calculate nutritional values that correspond to this total weight of {self.weight_grams}g.
Adjust your analysis to ensure the combined weight of all food items matches the target weight as closely as possible."""
    
    def get_strategy_name(self) -> str:
        return f"WeightAware({self.weight_grams}g)"

class AnalysisStrategyFactory:
    """
    Factory class for creating meal analysis strategies.
    """
    
    @staticmethod
    def create_basic_strategy() -> MealAnalysisStrategy:
        """Create a basic analysis strategy."""
        return BasicAnalysisStrategy()
    
    @staticmethod
    def create_portion_strategy(portion_size: float, unit: str) -> MealAnalysisStrategy:
        """Create a portion-aware analysis strategy."""
        return PortionAwareAnalysisStrategy(portion_size, unit)
    
    @staticmethod
    def create_ingredient_strategy(ingredients: List[Dict[str, Any]]) -> MealAnalysisStrategy:
        """Create an ingredient-aware analysis strategy."""
        return IngredientAwareAnalysisStrategy(ingredients)
    
    @staticmethod
    def create_weight_strategy(weight_grams: float) -> MealAnalysisStrategy:
        """Create a weight-aware analysis strategy."""
        return WeightAwareAnalysisStrategy(weight_grams)
    
    @staticmethod
    def create_combined_strategy(
        portion_size: Optional[float] = None, 
        unit: Optional[str] = None,
        ingredients: Optional[List[Dict[str, Any]]] = None
    ) -> MealAnalysisStrategy:
        """
        Create a combined strategy with both portion and ingredient context.
        
        Args:
            portion_size: Target portion size (optional)
            unit: Unit of portion size (optional)
            ingredients: List of ingredients (optional)
            
        Returns:
            MealAnalysisStrategy: Appropriate strategy based on provided context
        """
        if portion_size and unit and ingredients:
            # TODO: Implement CombinedAnalysisStrategy for future use
            logger.info("Combined strategy requested - using ingredient strategy for now")
            return IngredientAwareAnalysisStrategy(ingredients)
        elif portion_size and unit:
            return PortionAwareAnalysisStrategy(portion_size, unit)
        elif ingredients:
            return IngredientAwareAnalysisStrategy(ingredients)
        else:
            return BasicAnalysisStrategy() 