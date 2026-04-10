"""
MealInfoService — orchestrates meal name generation, nutrition description,
and image retrieval to build a MealInfo response.
"""
import logging
from typing import List, Optional

from src.domain.model.meal_info import MealInfo
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.meal_image_retrieval_service import MealImageRetrievalService
from src.domain.services.nutrition_description_service import NutritionDescriptionService

logger = logging.getLogger(__name__)

_NAME_SYSTEM = (
    "You are a professional chef. Return ONLY a concise, appetising meal name "
    "(3–8 words) for the described dish. No explanation, no punctuation at the end."
)

_DESC_SYSTEM = (
    "You are a nutrition expert. In 1–2 sentences describe the typical nutritional "
    "profile of this meal: mention key macros (high/low protein, carbs, fat) and one "
    "notable health benefit. Be specific and concise."
)


class MealInfoService:
    """Builds a complete MealInfo from user inputs."""

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        image_service: MealImageRetrievalService,
        description_service: NutritionDescriptionService,
    ):
        self._gen = generation_service
        self._img = image_service
        self._desc = description_service

    async def generate(
        self,
        meal_name: Optional[str],
        ingredients: Optional[List[str]],
        meal_type: str,
        calories: Optional[int],
        protein: Optional[float],
        carbs: Optional[float],
        fat: Optional[float],
    ) -> MealInfo:
        """
        Generate a MealInfo object.

        Steps:
        1. Resolve meal name (use provided or generate from ingredients).
        2. Build nutrition description (rule-based if macros given, else AI).
        3. Retrieve image via 3-source cascade.
        """
        # 1. Resolve meal name
        resolved_name = meal_name or await self._generate_name(ingredients or [], meal_type)

        # 2. Build nutrition description
        if all(v is not None for v in (calories, protein, carbs, fat)):
            nutrition_desc = self._desc.describe(
                calories=int(calories),
                protein=float(protein),
                carbs=float(carbs),
                fat=float(fat),
            )
        else:
            nutrition_desc = await self._generate_description_ai(resolved_name)

        # 3. Retrieve image
        image_url, image_source = await self._img.retrieve(resolved_name)

        return MealInfo(
            meal_name=resolved_name,
            nutrition_description=nutrition_desc,
            image_url=image_url,
            image_source=image_source,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _generate_name(self, ingredients: List[str], meal_type: str) -> str:
        ingredients_str = ", ".join(ingredients)
        prompt = f"Meal type: {meal_type}\nIngredients: {ingredients_str}"
        try:
            result = self._gen.generate_meal_plan(
                prompt=prompt,
                system_message=_NAME_SYSTEM,
                response_type="text",
                max_tokens=50,
            )
            raw = result.get("raw_content", "").strip()
            # Strip quotes if AI wrapped the name
            return raw.strip('"').strip("'") or "Mixed Dish"
        except Exception as exc:
            logger.warning("Meal name generation failed: %s", exc)
            if ingredients:
                return f"{meal_type.capitalize()} with {ingredients[0].title()}"
            return "Mixed Dish"

    async def _generate_description_ai(self, meal_name: str) -> str:
        try:
            result = self._gen.generate_meal_plan(
                prompt=f"Meal: {meal_name}",
                system_message=_DESC_SYSTEM,
                response_type="text",
                max_tokens=120,
            )
            return result.get("raw_content", "").strip() or "Nutritional information unavailable."
        except Exception as exc:
            logger.warning("AI nutrition description failed for '%s': %s", meal_name, exc)
            return "Nutritional information unavailable."
