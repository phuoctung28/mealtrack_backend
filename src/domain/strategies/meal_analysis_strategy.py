import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Shared decomposition instruction appended to all scanning strategies
SCAN_DECOMPOSITION_RULES = """
CRITICAL — INGREDIENT DECOMPOSITION:
- ALWAYS decompose compound dishes into individual ingredients
- If you see a bowl of soup: list broth, noodles, meat, vegetables separately
- If you see a sandwich: list bread, meat, cheese, sauce separately
- Never return compound dish names as single items (e.g. "pho" → list noodle, beef, broth, etc.)
- Simple single-ingredient items (banana, egg, plain rice) stay as 1 item
- Each ingredient: name, quantity (grams), unit, calories, macros

MACRO ACCURACY:
- All quantities in GRAMS (convert volumes using density: honey=1.42g/ml, oil=0.92g/ml)
- Verify: calories ≈ protein*4 + carbs*4 + fat*9

EMOJI SELECTION (for the "emoji" field):
- Return exactly ONE emoji that represents the OVERALL DISH, not individual ingredients
- Pick emoji based on the SERVING STYLE, not just the main ingredient:
  🍜 = noodle soup served in broth (phở, bún bò Huế, bún riêu, ramen, udon soup)
  🍝 = dry pasta/noodles without broth (spaghetti, mì xào, pad thai)
  🍚 = rice-based dishes (cơm, fried rice, bibimbap)
  🍛 = curry or saucy dish over rice
  🍲 = stew, hotpot, or thick soup (lẩu, canh, chowder)
  🥗 = salad or fresh/cold dishes (gỏi)
  🍖 = grilled/roasted meat dishes (bún chả, thịt nướng, BBQ)
  🥘 = braised/simmered dishes (kho, bò kho)
  🥟 = dumplings, spring rolls, wrapped items (nem, bánh cuốn, gyoza)
  🥪 = sandwiches, bánh mì
  🍳 = egg-based dishes (omelette, trứng chiên)
  🥣 = porridge, oatmeal, cháo
  🍱 = bento/meal box/combo platter
  🍗 = fried chicken, fried items
  🥩 = steak or large meat cuts
  🍕🍔🌮🌯 = pizza, burger, taco, burrito (Western fast food)
- If unsure, use 🍽️ as fallback
- NEVER return text or multiple emoji — exactly one emoji character
"""

# Compact rules for basic strategy prompts to meet length constraints
BASIC_SCAN_DECOMPOSITION_RULES = (
    "DECOMPOSE: split compound dishes into ingredients (soup→broth/noodles/meat/veg; "
    "sandwich→bread/meat/cheese/sauce). Single-ingredient foods may stay 1 item. "
    "Quantities in grams; calories ≈ protein*4 + carbs*4 + fat*9. "
    "EMOJI: return exactly one emoji for the overall dish by serving style "
    "(🍜 soup noodles, 🍝 dry noodles, 🍚 rice, 🍛 curry, 🍲 stew, 🥗 salad, 🍖 grilled, "
    "🥘 braised, 🥟 rolls, 🥪 sandwich, 🍳 egg, 🥣 porridge, 🍗 fried, 🥩 steak; fallback 🍽️)."
)


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

    def __init__(self, optimized_prompt_enabled: Optional[bool] = None):
        if optimized_prompt_enabled is None:
            optimized_prompt_enabled = True
        self.optimized_prompt_enabled = bool(optimized_prompt_enabled)

    def _legacy_analysis_prompt(self) -> str:
        return (
            "You are a nutrition analysis assistant. "
            "Examine the image and return JSON with dish_name, emoji, foods, "
            "total_calories, and confidence. "
            "Each food item includes name, quantity, unit, calories, and macros. "
            "Confidence should be between 0 and 1. "
            "Always return well-formed JSON."
        ) + SCAN_DECOMPOSITION_RULES

    def get_analysis_prompt(self) -> str:
        if not self.optimized_prompt_enabled:
            return self._legacy_analysis_prompt()

        return (
            "You are a nutrition analysis assistant. Return ONLY valid JSON with no commentary text:\n"
            "{\n"
            '  "dish_name": "Overall dish name or comma-separated items",\n'
            '  "emoji": "single emoji for the overall dish",\n'
            '  "foods": [\n'
            '    {"name": "Food name", "quantity": 1.0, "unit": "g", "calories": 100,\n'
            '     "macros": {"protein": 10, "carbs": 20, "fat": 5}}\n'
            "  ],\n"
            '  "total_calories": 100,\n'
            '  "confidence": 0.8\n'
            "}\n"
            "- Keep dish_name concise; if multiple items, use comma-separated names.\n"
            "- Each food item includes name, quantity, unit, calories, macros (grams).\n"
            "- Confidence between 0 and 1.\n"
            "- Max 8 food items.\n"
        ) + BASIC_SCAN_DECOMPOSITION_RULES

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
          "dish_name": "Overall dish name or comma-separated food items if complex",
          "emoji": "single food emoji that best represents this dish",
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
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.8,
          "portion_adjustment": "Adjusted for specified portion size"
        }

        - Include a dish_name field with the overall dish name (e.g., "Chicken Caesar Salad", "Spaghetti Bolognese")
        - If the foods are difficult to describe as a single dish, list them as comma-separated items (e.g., "grilled chicken, rice, broccoli")
        - Each food item should reflect the specified portion size
        - Calculate nutrition values proportionally to match the target portion
        - All macros should be in grams
        - Confidence should be between 0 (low) and 1 (high)
        - Include portion_adjustment field to indicate scaling was applied
        - Always return well-formed JSON
        """ + SCAN_DECOMPOSITION_RULES

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
          "dish_name": "Overall dish name or comma-separated food items if complex",
          "emoji": "single food emoji that best represents this dish",
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
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.9,
          "ingredient_based": true,
          "combined_nutrition": "Calculated based on provided ingredients"
        }

        - Include a dish_name field with the overall dish name (e.g., "Chicken Caesar Salad", "Spaghetti Bolognese")
        - If the foods are difficult to describe as a single dish, list them as comma-separated items (e.g., "grilled chicken, rice, broccoli")
        - Use the provided ingredient list to improve accuracy
        - Calculate total nutrition considering all ingredients combined
        - Account for cooking methods and ingredient interactions
        - Higher confidence scores are appropriate when ingredients are known
        - Include ingredient_based field to indicate enhanced analysis
        - Always return well-formed JSON
        """ + SCAN_DECOMPOSITION_RULES

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
          "dish_name": "Overall dish name or comma-separated food items if complex",
          "emoji": "single food emoji that best represents this dish",
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
              }
            }
          ],
          "total_calories": 100,
          "confidence": 0.85,
          "weight_adjustment": "Adjusted for specified total weight",
          "total_weight_grams": 300
        }

        - Include a dish_name field with the overall dish name (e.g., "Chicken Caesar Salad", "Spaghetti Bolognese")
        - If the foods are difficult to describe as a single dish, list them as comma-separated items (e.g., "grilled chicken, rice, broccoli")
        - Each food item should reflect proportions that add up to the target total weight
        - Calculate nutrition values to match the specified total weight
        - Use grams as the primary unit for quantities
        - All macros should be in grams
        - Higher confidence scores are appropriate with weight context
        - Include weight_adjustment and total_weight_grams fields
        - Always return well-formed JSON
        """ + SCAN_DECOMPOSITION_RULES

    def get_user_message(self) -> str:
        return f"""Analyze this food image and provide nutritional information.

WEIGHT CONTEXT: The user has specified that this meal should have a total weight of {self.weight_grams} grams.

Please examine the visual portions in the image and calculate nutritional values that correspond to this total weight of {self.weight_grams}g.
Adjust your analysis to ensure the combined weight of all food items matches the target weight as closely as possible."""

    def get_strategy_name(self) -> str:
        return f"WeightAware({self.weight_grams}g)"


class IngredientIdentificationStrategy(MealAnalysisStrategy):
    """
    Strategy for identifying a single ingredient from an image.

    Used when user takes a photo of an unknown food/ingredient and wants
    to identify it before getting meal suggestions.
    """

    def get_analysis_prompt(self) -> str:
        return """
        You are a food ingredient identification assistant.
        Identify the single food ingredient shown in this image.

        Return your analysis in the following JSON format:
        {
          "name": "ingredient name in English",
          "confidence": 0.95,
          "category": "vegetable|fruit|protein|grain|dairy|seasoning|other"
        }

        Guidelines:
        - Identify the PRIMARY/LARGEST ingredient if multiple are visible
        - Name should be in English, lowercase (e.g., "chicken breast", "broccoli", "salmon fillet")
        - Confidence between 0 (unsure) and 1 (certain)
        - Category must be one of: vegetable, fruit, protein, grain, dairy, seasoning, other
        - If no clear ingredient visible, return {"name": null, "confidence": 0, "category": null}
        - Always return well-formed JSON
        """

    def get_user_message(self) -> str:
        return "Identify the food ingredient in this image:"

    def get_strategy_name(self) -> str:
        return "IngredientIdentification"


class UserContextAwareAnalysisStrategy(MealAnalysisStrategy):
    """
    Analysis strategy that incorporates user-provided context.
    Used when user provides a description alongside their photo.

    NOTE: Content is generated in English. Translation to user's
    preferred language happens post-generation via TranslationService.
    """

    def __init__(self, user_description: str):
        self.user_description = user_description
        logger.info(
            f"Created UserContextAwareAnalysisStrategy: desc_len={len(user_description)}"
        )

    def get_analysis_prompt(self) -> str:
        return """
You are a nutrition analysis assistant that can analyze food in images.
Examine the image carefully and provide detailed nutritional information.

**IMPORTANT**: The user has provided additional context about this meal.
Use their description to ENHANCE accuracy, especially for:
- Modifications (sugar, sauce, oil levels)
- Hidden ingredients (cheese inside, sauce on side)
- Preparation method (fried vs baked vs grilled)
- Portion context (half portion, extra large)

**CONFLICT RESOLUTION**:
- PRIORITIZE VISUAL for: food identification, base ingredients
- PRIORITIZE USER INPUT for: modifications, hidden items, preparation

Return your analysis in the following JSON format:
{
  "dish_name": "Overall dish name",
  "emoji": "single food emoji that best represents this dish",
  "foods": [
    {
      "name": "Food name",
      "quantity": 1.0,
      "unit": "serving/g/oz/cup/etc",
      "calories": 100,
      "macros": {"protein": 10, "carbs": 20, "fat": 5}
    }
  ],
  "total_calories": 100,
  "confidence": 0.85,
  "user_context_applied": true
}

- Include a dish_name field with the overall dish name
- Each food item should include name, estimated quantity, unit of measurement, calories, and macros
- All macros should be in grams
- Confidence should be between 0 (low) and 1 (high) based on how certain you are
- Set user_context_applied: true to indicate user context was used
- Always return well-formed JSON
""" + SCAN_DECOMPOSITION_RULES

    def get_user_message(self) -> str:
        return f"""Analyze this food image and provide nutritional information.

USER CONTEXT: {self.user_description}

Use the user's description to improve your analysis accuracy."""

    def get_strategy_name(self) -> str:
        return "UserContextAware"


class AnalysisStrategyFactory:
    """
    Factory class for creating meal analysis strategies.

    NOTE: Strategies generate content in English. Translation to user's
    preferred language happens post-generation via TranslationService.
    """

    @staticmethod
    def create_basic_strategy(
        optimized_prompt_enabled: Optional[bool] = None,
    ) -> MealAnalysisStrategy:
        """Create a basic analysis strategy."""
        return BasicAnalysisStrategy(
            optimized_prompt_enabled=optimized_prompt_enabled
        )

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
    def create_ingredient_identification_strategy() -> MealAnalysisStrategy:
        """Create an ingredient identification strategy for photo recognition."""
        return IngredientIdentificationStrategy()

    @staticmethod
    def create_user_context_strategy(user_description: str) -> MealAnalysisStrategy:
        """Create a user-context-aware analysis strategy.

        Args:
            user_description: Sanitized user-provided description

        Returns:
            MealAnalysisStrategy: Strategy that incorporates user context
        """
        return UserContextAwareAnalysisStrategy(user_description)

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
