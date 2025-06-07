from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from api.schemas.ingredient_schemas import (
    CreateIngredientRequest, UpdateIngredientRequest, IngredientResponse,
    IngredientCreatedResponse, IngredientUpdatedResponse, IngredientDeletedResponse,
    IngredientListResponse
)
from api.dependencies import get_meal_ingredient_service, get_upload_meal_image_handler
from app.services.meal_ingredient_service import MealIngredientService
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals/{meal_id}/ingredients",
    tags=["ingredients"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=IngredientCreatedResponse)
async def add_ingredient(
    meal_id: str,
    ingredient_data: CreateIngredientRequest,
    background_tasks: BackgroundTasks,
    ingredient_service: MealIngredientService = Depends(get_meal_ingredient_service),
    meal_handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """
    Add meal ingredients will update the macros of the meal.
    
    - Creates a new ingredient for the specified meal
    - Triggers LLM-based recalculation of meal macros
    - Must priority endpoint for accurate nutrition calculation
    """
    try:
        logger.info(f"Adding ingredient {ingredient_data.name} to meal {meal_id}")
        
        # Add ingredient to the service
        ingredient_id = ingredient_service.add_ingredient(
            meal_id=meal_id,
            name=ingredient_data.name,
            quantity=ingredient_data.quantity,
            unit=ingredient_data.unit,
            calories=ingredient_data.calories,
            macros=ingredient_data.macros.dict() if ingredient_data.macros else None
        )
        
        # Create ingredient response
        ingredient_response = IngredientResponse(
            ingredient_id=ingredient_id,
            meal_id=meal_id,
            name=ingredient_data.name,
            quantity=ingredient_data.quantity,
            unit=ingredient_data.unit,
            calories=ingredient_data.calories,
            macros=ingredient_data.macros,
            created_at="2024-01-01T00:00:00Z"
        )
        
        # Schedule LLM-based nutrition recalculation with all ingredients
        logger.info(f"Triggering LLM recalculation for meal {meal_id} with all ingredients")
        
        # Get all ingredients for context
        all_ingredients = ingredient_service.get_ingredients_context_for_llm(meal_id)
        
        # Add background task to recalculate nutrition with ingredients context
        background_tasks.add_task(
            _recalculate_meal_with_ingredients,
            meal_id,
            all_ingredients,
            meal_handler
        )
        
        # Return immediate response
        return IngredientCreatedResponse(
            ingredient=ingredient_response,
            message=f"Ingredient added successfully - LLM recalculating nutrition with {len(all_ingredients)} ingredients",
            updated_meal_macros={
                "protein": 25.0,  # Placeholder - LLM will calculate accurate values
                "carbs": 30.0,
                "fat": 10.0,
                "fiber": 5.0
            }
        )
        
    except Exception as e:
        logger.error(f"Error adding ingredient to meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding ingredient: {str(e)}"
        )


def _recalculate_meal_with_ingredients(meal_id: str, ingredients: list, handler: UploadMealImageHandler):
    """
    Background task to recalculate meal nutrition after adding ingredients using LLM.
    
    Args:
        meal_id: ID of the meal to recalculate
        ingredients: List of all ingredients in the meal
        handler: Upload meal image handler with LLM integration
    """
    try:
        logger.info(f"Background task: Recalculating meal {meal_id} with {len(ingredients)} ingredients")
        
        # Use the specialized ingredient-aware analysis method
        handler.analyze_meal_with_ingredients_background(meal_id, ingredients)
        
        logger.info(f"Background task: Completed ingredient-based recalculation for meal {meal_id}")
        
    except Exception as e:
        logger.error(f"Background task: Error recalculating meal {meal_id} with ingredients: {str(e)}", exc_info=True)

@router.get("/", response_model=IngredientListResponse)
async def get_ingredients(
    meal_id: str,
    ingredient_service: MealIngredientService = Depends(get_meal_ingredient_service),
):
    """
    Get all ingredients for a specific meal.
    
    - Returns list of all ingredients belonging to the meal
    """
    try:
        logger.info(f"Retrieving ingredients for meal {meal_id}")
        
        # Get ingredients from service
        ingredients = ingredient_service.get_ingredients_for_meal(meal_id)
        
        # Convert to response format
        ingredient_responses = []
        for ingredient in ingredients:
            ingredient_responses.append(IngredientResponse(
                ingredient_id=ingredient.ingredient_id,
                meal_id=ingredient.meal_id,
                name=ingredient.name,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                calories=ingredient.calories,
                macros=ingredient.macros,
                created_at="2024-01-01T00:00:00Z"
            ))
        
        return IngredientListResponse(
            ingredients=ingredient_responses,
            total_count=len(ingredient_responses),
            meal_id=meal_id
        )
        
    except Exception as e:
        logger.error(f"Error retrieving ingredients for meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ingredients: {str(e)}"
        )

@router.put("/{ingredient_id}", response_model=IngredientUpdatedResponse)
async def update_ingredient(
    meal_id: str,
    ingredient_id: str,
    ingredient_data: UpdateIngredientRequest,
    # handler: IngredientHandler = Depends(get_ingredient_handler)
):
    """
    Update meal ingredients will update the macros of the meal.
    
    - Updates existing ingredient
    - Automatically recalculates meal macros based on updated ingredients
    - Must priority endpoint
    """
    try:
        # TODO: Implement ingredient update and meal macro recalculation
        logger.info(f"Updating ingredient {ingredient_id} for meal {meal_id}")
        
        # Placeholder response - implement actual update
        ingredient_response = IngredientResponse(
            ingredient_id=ingredient_id,
            meal_id=meal_id,
            name=ingredient_data.name or "Updated Ingredient",
            quantity=ingredient_data.quantity or 75.0,
            unit=ingredient_data.unit or "g",
            calories=ingredient_data.calories or 150.0,
            macros=ingredient_data.macros or {
                "protein": 15.0,
                "carbs": 20.0,
                "fat": 7.0,
                "fiber": 3.0
            },
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T12:00:00Z"
        )
        
        return IngredientUpdatedResponse(
            ingredient=ingredient_response,
            message="Ingredient updated successfully",
            updated_meal_macros={
                "protein": 28.0,
                "carbs": 32.0,
                "fat": 11.0,
                "fiber": 6.0
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating ingredient {ingredient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating ingredient: {str(e)}"
        )

@router.delete("/{ingredient_id}", response_model=IngredientDeletedResponse)
async def delete_ingredient(
    meal_id: str,
    ingredient_id: str,
    # handler: IngredientHandler = Depends(get_ingredient_handler)
):
    """
    Delete meal ingredients will update the macros of the meal.
    
    - Deletes existing ingredient
    - Automatically recalculates meal macros after deletion
    - Must priority endpoint
    """
    try:
        # TODO: Implement ingredient deletion and meal macro recalculation
        logger.info(f"Deleting ingredient {ingredient_id} from meal {meal_id}")
        
        # Placeholder response - implement actual deletion
        return IngredientDeletedResponse(
            message="Ingredient deleted successfully",
            deleted_ingredient_id=ingredient_id,
            meal_id=meal_id,
            updated_meal_macros={
                "protein": 20.0,
                "carbs": 25.0,
                "fat": 8.0,
                "fiber": 4.0
            }
        )
        
    except Exception as e:
        logger.error(f"Error deleting ingredient {ingredient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting ingredient: {str(e)}"
        ) 