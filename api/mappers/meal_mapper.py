"""
Meal Mapper

Handles conversion between Meal domain models and DTOs.
Follows the Mapper Pattern for clean separation of concerns.
"""

import logging

from api.schemas import (
    DetailedMealResponse,
    MealResponse,
    MealStatusResponse,
    ImageSchema,
    IngredientBreakdownSchema
)
from app.models import NutritionSummarySchema, MacrosSchema
from domain.model.meal import Meal

logger = logging.getLogger(__name__)


class MealMapper:
    """
    Mapper class for converting between Meal domain models and DTOs.
    
    This class encapsulates all the conversion logic, keeping handlers
    focused on business orchestration rather than data transformation.
    """
    
    @staticmethod
    def to_detailed_response(meal: Meal, ingredients: list[IngredientBreakdownSchema] = None, meal_name: str = None) -> DetailedMealResponse:
        """
        Convert a domain Meal model to a DetailedMealResponse DTO.
        
        Args:
            meal: Domain meal model
            ingredients: Pre-extracted ingredient breakdown data (from app layer)
            meal_name: Optional meal name from AI analysis (overrides default extraction)
            
        Returns:
            DetailedMealResponse DTO
        """
        # Create image response
        image_response = ImageSchema(
            image_id=meal.image.image_id,
            format=meal.image.format,
            size_bytes=meal.image.size_bytes,
            width=meal.image.width,
            height=meal.image.height,
            url=meal.image.url if hasattr(meal.image, 'url') else None
        )
        
        # Create simplified nutrition response if available
        nutrition_response = None
        if meal.nutrition:
            nutrition_response = MealMapper._create_nutrition_summary(meal, meal_name)
        
        # Create complete meal response
        return DetailedMealResponse(
            meal_id=meal.meal_id,
            status=meal.status.value,
            created_at=meal.created_at,
            image=image_response,
            nutrition=nutrition_response,
            ingredients=ingredients,
            error_message=meal.error_message,
            ready_at=getattr(meal, "ready_at", None)
        )
    
    @staticmethod
    def to_response(meal: Meal) -> MealResponse:
        """
        Convert a domain Meal model to a standard MealResponse DTO.
        
        Args:
            meal: Domain meal model
            
        Returns:
            MealResponse DTO
        """
        # Calculate nutrition values if available
        total_calories = None
        calories_per_100g = None
        macros_per_100g = None
        total_macros = None
        weight_grams = None
        
        if meal.nutrition:
            weight_grams = MealMapper._get_estimated_weight(meal)
            total_calories, total_macros = MealMapper._calculate_total_nutrition(meal, weight_grams)
            calories_per_100g, macros_per_100g = MealMapper._calculate_per_100g_nutrition(
                total_calories, total_macros, weight_grams
            )
        
        return MealResponse(
            meal_id=meal.meal_id,
            name=meal.name if hasattr(meal, 'name') else None,
            description=meal.description if hasattr(meal, 'description') else None,
            weight_grams=weight_grams,
            total_calories=total_calories,
            calories_per_100g=calories_per_100g,
            macros_per_100g=macros_per_100g,
            total_macros=total_macros,
            status=meal.status.value,
            created_at=meal.created_at,
            updated_at=getattr(meal, 'updated_at', None),
            ready_at=getattr(meal, 'ready_at', None),
            error_message=meal.error_message,
            image_url=meal.image.url if hasattr(meal.image, 'url') else None
        )
    
    @staticmethod
    def to_status_response(meal: Meal, status_message: str) -> MealStatusResponse:
        """
        Convert a domain Meal model to a MealStatusResponse DTO.
        
        Args:
            meal: Domain meal model
            status_message: Human-readable status message
            
        Returns:
            MealStatusResponse DTO
        """
        return MealStatusResponse(
            meal_id=meal.meal_id,
            status=meal.status.value,
            status_message=status_message,
            error_message=meal.error_message
        )
    
    @staticmethod
    def to_response_with_updated_nutrition(
        meal: Meal,
        weight_grams: float,
        total_calories: float,
        calories_per_100g: float,
        macros_per_100g,
        total_macros,
        description: str
    ) -> MealResponse:
        """
        Convert domain Meal to MealResponse DTO with updated nutrition data.
        
        Used specifically for weight update responses with calculated nutrition.
        
        Args:
            meal: Domain meal model
            weight_grams: Updated weight
            total_calories: Calculated total calories
            calories_per_100g: Calculated calories per 100g
            macros_per_100g: Calculated macros per 100g
            total_macros: Calculated total macros
            description: Response description
            
        Returns:
            MealResponse DTO
        """
        return MealResponse(
            meal_id=meal.meal_id,
            name=meal.name if hasattr(meal, 'name') else "Meal",
            description=description,
            weight_grams=weight_grams,
            total_calories=total_calories,
            calories_per_100g=calories_per_100g,
            macros_per_100g=macros_per_100g,
            total_macros=total_macros,
            status=meal.status.value,
            created_at=meal.created_at.isoformat() if meal.created_at else "2024-01-01T00:00:00Z",
            updated_at=meal.updated_at.isoformat() if hasattr(meal, 'updated_at') and meal.updated_at else "2024-01-01T12:00:00Z"
        )
    
    @staticmethod
    def _create_nutrition_summary(meal: Meal, meal_name: str = None) -> NutritionSummarySchema:
        """
        Create a nutrition summary from meal nutrition data.
        
        Args:
            meal: Domain meal model with nutrition
            meal_name: Optional meal name from AI analysis (overrides default extraction)
            
        Returns:
            NutritionSummarySchema
        """
        # Extract meal name from first food item or use a default
        if meal_name:
            # Use provided meal name from AI analysis
            final_meal_name = meal_name
        else:
            # Fallback to extracting from food items or default
            final_meal_name = "Unknown Meal"
            if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
                final_meal_name = meal.nutrition.food_items[0].name
        
        # Get estimated weight
        estimated_weight = MealMapper._get_estimated_weight(meal)
        
        # Calculate total nutrition values
        total_calories, total_macros = MealMapper._calculate_total_nutrition(meal, estimated_weight)
        
        # Calculate per-100g values
        calories_per_100g, macros_per_100g = MealMapper._calculate_per_100g_nutrition(
            total_calories, total_macros, estimated_weight
        )
        
        return NutritionSummarySchema(
            meal_name=final_meal_name,
            total_calories=total_calories,
            total_weight_grams=estimated_weight,
            calories_per_100g=calories_per_100g,
            macros_per_100g=macros_per_100g,
            total_macros=total_macros,
            confidence_score=meal.nutrition.confidence_score
        )
    
    @staticmethod
    def _get_estimated_weight(meal: Meal) -> float:
        """
        Get estimated weight for the meal.
        
        Args:
            meal: Domain meal model
            
        Returns:
            Estimated weight in grams
        """
        # Check if meal has been updated with new weight
        if hasattr(meal, 'updated_weight_grams'):
            return meal.updated_weight_grams
        
        # Default estimated weight
        estimated_weight = 300.0
        
        # Try to extract weight from food items
        if hasattr(meal.nutrition, 'food_items') and meal.nutrition.food_items:
            first_food = meal.nutrition.food_items[0]
            if first_food.unit and 'g' in first_food.unit.lower():
                estimated_weight = first_food.quantity
            elif first_food.quantity > 10:  # Assume grams if quantity is large
                estimated_weight = first_food.quantity
        
        return estimated_weight
    
    @staticmethod
    def _calculate_total_nutrition(meal: Meal, weight_grams: float) -> tuple[float, MacrosSchema]:
        """
        Calculate total nutrition values based on weight.
        
        Args:
            meal: Domain meal model
            weight_grams: Weight in grams
            
        Returns:
            Tuple of (total_calories, total_macros)
        """
        # Create base macros response
        macros_response = MacrosSchema(
            protein=meal.nutrition.macros.protein,
            carbs=meal.nutrition.macros.carbs,
            fat=meal.nutrition.macros.fat,
            fiber=meal.nutrition.macros.fiber if hasattr(meal.nutrition.macros, 'fiber') else None
        )
        
        # Calculate nutrition values based on current weight
        if hasattr(meal, 'updated_weight_grams') and hasattr(meal, 'original_weight_grams'):
            # Meal has been updated - scale nutrition accordingly
            ratio = meal.updated_weight_grams / meal.original_weight_grams
            total_calories = meal.nutrition.calories * ratio
            total_macros = MacrosSchema(
                protein=macros_response.protein * ratio,
                carbs=macros_response.carbs * ratio,
                fat=macros_response.fat * ratio,
                fiber=macros_response.fiber * ratio if macros_response.fiber else None
            )
        else:
            # Use original nutrition values
            total_calories = meal.nutrition.calories
            total_macros = macros_response
        
        return total_calories, total_macros
    
    @staticmethod
    def _calculate_per_100g_nutrition(
        total_calories: float, 
        total_macros: MacrosSchema, 
        weight_grams: float
    ) -> tuple[float, MacrosSchema]:
        """
        Calculate per-100g nutrition values.
        
        Args:
            total_calories: Total calories
            total_macros: Total macros
            weight_grams: Weight in grams
            
        Returns:
            Tuple of (calories_per_100g, macros_per_100g)
        """
        weight_ratio = weight_grams / 100.0
        
        calories_per_100g = total_calories / weight_ratio if weight_ratio > 0 else total_calories
        
        macros_per_100g = MacrosSchema(
            protein=total_macros.protein / weight_ratio if weight_ratio > 0 else total_macros.protein,
            carbs=total_macros.carbs / weight_ratio if weight_ratio > 0 else total_macros.carbs,
            fat=total_macros.fat / weight_ratio if weight_ratio > 0 else total_macros.fat,
            fiber=total_macros.fiber / weight_ratio if weight_ratio > 0 and total_macros.fiber else total_macros.fiber
        )
        
        return calories_per_100g, macros_per_100g

    @staticmethod
    def convert_ingredient_data_to_dtos(ingredient_data_list) -> list[IngredientBreakdownSchema]:
        """
        Convert app layer IngredientData objects to API DTOs.
        
        Args:
            ingredient_data_list: List of IngredientData from app layer
            
        Returns:
            List of IngredientBreakdownSchema DTOs
        """
        if not ingredient_data_list:
            return None
        
        # Import here to avoid circular imports

        ingredient_dtos = []
        for ingredient_data in ingredient_data_list:
            # Convert domain macros to DTO macros
            macros_dto = MacrosSchema(
                protein=ingredient_data.macros.protein,
                carbs=ingredient_data.macros.carbs,
                fat=ingredient_data.macros.fat,
                fiber=ingredient_data.macros.fiber
            )
            
            # Create ingredient DTO
            ingredient_dto = IngredientBreakdownSchema(
                name=ingredient_data.name,
                quantity=ingredient_data.quantity,
                unit=ingredient_data.unit,
                calories=ingredient_data.calories,
                macros=macros_dto
            )
            
            ingredient_dtos.append(ingredient_dto)
        
        return ingredient_dtos

 