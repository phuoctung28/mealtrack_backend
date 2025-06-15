"""
Ingredient Mapper

Handles conversion between Ingredient domain models and DTOs.
Follows the Mapper Pattern for clean separation of concerns.
"""

from typing import List

from api.schemas import (
    CreateIngredientRequest,
    UpdateIngredientRequest,
    IngredientResponse,
    IngredientCreatedResponse,
    IngredientUpdatedResponse,
    IngredientDeletedResponse,
    IngredientListResponse
)
from app.models import MacrosSchema


class IngredientMapper:
    """
    Mapper class for converting between Ingredient domain models and DTOs.
    
    This class encapsulates all the conversion logic for ingredient management,
    keeping handlers focused on business orchestration.
    """
    
    @staticmethod
    def to_response(ingredient) -> IngredientResponse:
        """
        Convert a domain Ingredient model to an IngredientResponse DTO.
        
        Args:
            ingredient: Domain ingredient model
            
        Returns:
            IngredientResponse DTO
        """
        macros = None
        if ingredient.macros:
            macros = MacrosSchema(
                protein=ingredient.macros.protein,
                carbs=ingredient.macros.carbs,
                fat=ingredient.macros.fat,
                fiber=ingredient.macros.fiber if hasattr(ingredient.macros, 'fiber') else None
            )
        
        return IngredientResponse(
            ingredient_id=ingredient.ingredient_id,
            meal_id=ingredient.meal_id,
            name=ingredient.name,
            quantity=ingredient.quantity,
            unit=ingredient.unit,
            calories=ingredient.calories,
            macros=macros,
            created_at=ingredient.created_at.isoformat() if ingredient.created_at else None,
            updated_at=ingredient.updated_at.isoformat() if hasattr(ingredient, 'updated_at') and ingredient.updated_at else None
        )
    
    @staticmethod
    def to_created_response(
        ingredient,
        updated_meal_macros: MacrosSchema = None
    ) -> IngredientCreatedResponse:
        """
        Convert to a creation success response.
        
        Args:
            ingredient: Domain ingredient model
            updated_meal_macros: Updated meal macros after adding ingredient
            
        Returns:
            IngredientCreatedResponse DTO
        """
        return IngredientCreatedResponse(
            ingredient=IngredientMapper.to_response(ingredient),
            message="Ingredient added successfully",
            updated_meal_macros=updated_meal_macros
        )
    
    @staticmethod
    def to_updated_response(
        ingredient,
        updated_meal_macros: MacrosSchema = None
    ) -> IngredientUpdatedResponse:
        """
        Convert to an update success response.
        
        Args:
            ingredient: Domain ingredient model
            updated_meal_macros: Updated meal macros after updating ingredient
            
        Returns:
            IngredientUpdatedResponse DTO
        """
        return IngredientUpdatedResponse(
            ingredient=IngredientMapper.to_response(ingredient),
            message="Ingredient updated successfully",
            updated_meal_macros=updated_meal_macros
        )
    
    @staticmethod
    def to_deleted_response(
        ingredient_id: str,
        meal_id: str,
        updated_meal_macros: MacrosSchema = None
    ) -> IngredientDeletedResponse:
        """
        Convert to a deletion success response.
        
        Args:
            ingredient_id: ID of deleted ingredient
            meal_id: ID of the parent meal
            updated_meal_macros: Updated meal macros after deleting ingredient
            
        Returns:
            IngredientDeletedResponse DTO
        """
        return IngredientDeletedResponse(
            message="Ingredient deleted successfully",
            deleted_ingredient_id=ingredient_id,
            meal_id=meal_id,
            updated_meal_macros=updated_meal_macros
        )
    
    @staticmethod
    def to_list_response(
        ingredients: List,
        meal_id: str
    ) -> IngredientListResponse:
        """
        Convert a list of ingredients to a list response.
        
        Args:
            ingredients: List of domain ingredient models
            meal_id: ID of the parent meal
            
        Returns:
            IngredientListResponse DTO
        """
        ingredient_responses = [
            IngredientMapper.to_response(ingredient) for ingredient in ingredients
        ]
        
        return IngredientListResponse(
            ingredients=ingredient_responses,
            total_count=len(ingredient_responses),
            meal_id=meal_id
        )
    
    @staticmethod
    def from_create_request(request: CreateIngredientRequest, ingredient_id: str, meal_id: str):
        """
        Convert a CreateIngredientRequest DTO to domain ingredient data.
        
        Args:
            request: CreateIngredientRequest DTO
            ingredient_id: Generated ingredient ID
            meal_id: Parent meal ID
            
        Returns:
            Dictionary with ingredient data for domain model creation
        """
        macros_data = None
        if request.macros:
            macros_data = {
                "protein": request.macros.protein,
                "carbs": request.macros.carbs,
                "fat": request.macros.fat,
                "fiber": request.macros.fiber
            }
        
        return {
            "ingredient_id": ingredient_id,
            "meal_id": meal_id,
            "name": request.name,
            "quantity": request.quantity,
            "unit": request.unit,
            "calories": request.calories,
            "macros": macros_data
        }
    
    @staticmethod
    def from_update_request(request: UpdateIngredientRequest):
        """
        Convert an UpdateIngredientRequest DTO to update data.
        
        Args:
            request: UpdateIngredientRequest DTO
            
        Returns:
            Dictionary with update data (only non-None values)
        """
        update_data = {}
        
        if request.name is not None:
            update_data["name"] = request.name
        if request.quantity is not None:
            update_data["quantity"] = request.quantity
        if request.unit is not None:
            update_data["unit"] = request.unit
        if request.calories is not None:
            update_data["calories"] = request.calories
        if request.macros is not None:
            update_data["macros"] = {
                "protein": request.macros.protein,
                "carbs": request.macros.carbs,
                "fat": request.macros.fat,
                "fiber": request.macros.fiber
            }
        
        return update_data 