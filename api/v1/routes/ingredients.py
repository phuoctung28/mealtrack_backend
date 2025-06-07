import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends

from api.dependencies import get_meal_ingredient_service, get_upload_meal_image_handler
from api.schemas.ingredient_schemas import CreateIngredientRequest
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from app.services.meal_ingredient_service import MealIngredientService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals/{meal_id}/ingredients",
    tags=["ingredients"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict)
async def add_ingredients(
    meal_id: str,
    ingredients: List[CreateIngredientRequest],
    ingredient_service: MealIngredientService = Depends(get_meal_ingredient_service),
    meal_handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """Add ingredients to meal and trigger LLM-based macro recalculation."""
    try:
        logger.info(f"Adding {len(ingredients)} ingredients to meal {meal_id}")
        
        # Convert to dictionaries for the service
        ingredient_dicts = []
        for ingredient in ingredients:
            ingredient_dict = {
                "name": ingredient.name,
                "quantity": ingredient.quantity,
                "unit": ingredient.unit,
                "calories": ingredient.calories,
                "macros": ingredient.macros.dict() if ingredient.macros else None
            }
            ingredient_dicts.append(ingredient_dict)
        
        # Add ingredients and trigger LLM recalculation
        result = await meal_handler.add_ingredients_to_meal(meal_id, ingredient_dicts)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding ingredients to meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding ingredients: {str(e)}"
        )

@router.get("/", response_model=List[Dict[str, Any]])
async def get_ingredients(
    meal_id: str,
    ingredient_service: MealIngredientService = Depends(get_meal_ingredient_service),
):
    """Get all ingredients for a specific meal."""
    try:
        logger.info(f"Retrieving ingredients for meal {meal_id}")
        
        ingredients = ingredient_service.get_ingredients_for_meal(meal_id)
        
        return ingredients
        
    except Exception as e:
        logger.error(f"Error retrieving ingredients for meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ingredients: {str(e)}"
        ) 