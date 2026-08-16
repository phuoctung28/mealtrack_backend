"""Map immutable catalog meals to shared recommendation and browse DTOs."""

from src.api.schemas.response.meal_catalog_responses import MealCatalogItemResponse
from src.api.schemas.response.meal_recommendation_responses import (
    MealRecommendationCatalogMealResponse,
    MealRecommendationIngredientResponse,
    MealRecommendationMacrosResponse,
)
from src.domain.model.meal_recommendation import CatalogMeal


def catalog_meal_response(
    catalog_meal: CatalogMeal,
) -> MealRecommendationCatalogMealResponse:
    return MealRecommendationCatalogMealResponse(
        id=catalog_meal.id,
        name=catalog_meal.name,
        cuisine=catalog_meal.cuisine,
        description=catalog_meal.description,
        image_url=catalog_meal.image_url,
        calories=catalog_meal.calories,
        macros=MealRecommendationMacrosResponse(
            protein_g=float(catalog_meal.protein_g),
            carbs_g=float(catalog_meal.carbs_g),
            fat_g=float(catalog_meal.fat_g),
            fiber_g=float(catalog_meal.fiber_g),
            sugar_g=float(catalog_meal.sugar_g),
        ),
        ingredients=catalog_meal_ingredients(catalog_meal),
    )


def catalog_meal_browse_response(catalog_meal: CatalogMeal) -> MealCatalogItemResponse:
    response = catalog_meal_response(catalog_meal)
    return MealCatalogItemResponse(
        **response.model_dump(),
        meal_types=list(catalog_meal.meal_types),
        ingredient_count=len(catalog_meal.ingredients),
    )


def catalog_meal_ingredients(
    catalog_meal: CatalogMeal,
) -> list[MealRecommendationIngredientResponse]:
    return [
        MealRecommendationIngredientResponse(
            food_reference_id=ingredient.food_reference_id,
            display_name=ingredient.display_name,
            quantity=float(ingredient.quantity),
            unit=ingredient.unit,
        )
        for ingredient in catalog_meal.ingredients
    ]
