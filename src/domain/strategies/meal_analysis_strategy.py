import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.services.prompts.system_prompts import SystemPrompts

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

    def __init__(self, optimized_prompt_enabled: Optional[bool] = None):
        if optimized_prompt_enabled is None:
            optimized_prompt_enabled = True
        self.optimized_prompt_enabled = bool(optimized_prompt_enabled)

    def get_analysis_prompt(self) -> str:
        return SystemPrompts.VISION_ANALYSIS

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
        return SystemPrompts.VISION_ANALYSIS

    def get_user_message(self) -> str:
        return (
            f"Analyze this food image.\n"
            f"Portion context: {self.portion_size} {self.unit}. "
            f"Scale all nutrition values to match this portion."
        )

    def get_strategy_name(self) -> str:
        return f"PortionAware({self.portion_size}{self.unit})"


class IngredientAwareAnalysisStrategy(MealAnalysisStrategy):
    """
    Ingredient-aware meal analysis strategy.
    """

    def __init__(self, ingredients: List[Dict[str, Any]]):
        self.ingredients = ingredients
        logger.info(
            f"Created IngredientAwareAnalysisStrategy with {len(ingredients)} ingredients"
        )

    def get_analysis_prompt(self) -> str:
        return SystemPrompts.VISION_ANALYSIS

    def get_user_message(self) -> str:
        ing_str = ", ".join(
            f"{i.get('name', '')} ({i.get('quantity', '')} {i.get('unit', '')})"
            for i in self.ingredients[:6]
        )
        return (
            f"Analyze this food image.\n"
            f"Known ingredients: {ing_str}. "
            f"Use this context to improve accuracy."
        )

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
        return SystemPrompts.VISION_ANALYSIS

    def get_user_message(self) -> str:
        return (
            f"Analyze this food image.\n"
            f"Total weight: {self.weight_grams}g. "
            f"Scale all nutrition values proportionally to this total weight."
        )

    def get_strategy_name(self) -> str:
        return f"WeightAware({self.weight_grams}g)"


class IngredientIdentificationStrategy(MealAnalysisStrategy):
    """
    Strategy for identifying a single ingredient from an image.

    Used when user takes a photo of an unknown food/ingredient and wants
    to identify it before getting meal suggestions.
    """

    def get_analysis_prompt(self) -> str:
        return SystemPrompts.INGREDIENT_IDENTIFY

    def get_user_message(self) -> str:
        return "Identify the food ingredient in this image:"

    def get_strategy_name(self) -> str:
        return "IngredientIdentification"


class FoodLabelAnalysisStrategy(MealAnalysisStrategy):
    """Strategy for extracting packaged food Nutrition Facts labels."""

    def get_analysis_prompt(self) -> str:
        return SystemPrompts.FOOD_LABEL_ANALYSIS

    def get_user_message(self) -> str:
        return "Extract the visible Nutrition Facts label for one serving:"

    def get_strategy_name(self) -> str:
        return "FoodLabelAnalysis"


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
        return SystemPrompts.VISION_ANALYSIS

    def get_user_message(self) -> str:
        return (
            f"Analyze this food image.\n"
            f"User context: {self.user_description}. "
            f"Provide accurate nutrition data for this meal."
        )

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
        return BasicAnalysisStrategy(optimized_prompt_enabled=optimized_prompt_enabled)

    @staticmethod
    def create_portion_strategy(portion_size: float, unit: str) -> MealAnalysisStrategy:
        """Create a portion-aware analysis strategy."""
        return PortionAwareAnalysisStrategy(portion_size, unit)

    @staticmethod
    def create_ingredient_strategy(
        ingredients: List[Dict[str, Any]],
    ) -> MealAnalysisStrategy:
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
    def create_food_label_strategy() -> MealAnalysisStrategy:
        """Create a packaged food-label extraction strategy."""
        return FoodLabelAnalysisStrategy()

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
        ingredients: Optional[List[Dict[str, Any]]] = None,
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
            logger.info(
                "Combined strategy requested - using ingredient strategy for now"
            )
            return IngredientAwareAnalysisStrategy(ingredients)
        elif portion_size and unit:
            return PortionAwareAnalysisStrategy(portion_size, unit)
        elif ingredients:
            return IngredientAwareAnalysisStrategy(ingredients)
        else:
            return BasicAnalysisStrategy()
