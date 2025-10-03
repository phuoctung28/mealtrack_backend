"""
Meal-related request DTOs.
"""
from typing import Optional, Literal

from pydantic import BaseModel, Field, validator


class MacrosRequest(BaseModel):
    """Request DTO for macronutrient information."""
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")


class CreateMealRequest(BaseModel):
    """Request DTO for creating a meal manually."""
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, le=5000, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosRequest] = Field(None, description="Macros per 100g")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Grilled Chicken Breast",
                "description": "Seasoned with herbs and olive oil",
                "weight_grams": 150,
                "calories_per_100g": 165,
                "macros_per_100g": {
                    "protein": 31.0,
                    "carbs": 0,
                    "fat": 3.6
                }
            }
        }


class UpdateMealRequest(BaseModel):
    """Request DTO for updating meal information."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, le=5000, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosRequest] = Field(None, description="Macros per 100g")


class UpdateMealMacrosRequest(BaseModel):
    """Request DTO for updating meal portion size."""
    weight_grams: float = Field(
        ..., 
        gt=0, 
        le=5000, 
        description="Weight of the meal portion in grams"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "weight_grams": 250.0
            }
        }


class MealSearchRequest(BaseModel):
    """Request DTO for searching meals."""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    include_ingredients: bool = Field(False, description="Include ingredients in search")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "chicken",
                "limit": 20,
                "include_ingredients": True
            }
        }


class AnalyzeMealImageRequest(BaseModel):
    """Request DTO for meal image analysis options."""
    immediate_analysis: bool = Field(
        False, 
        description="Perform immediate analysis (synchronous)"
    )
    portion_size_grams: Optional[float] = Field(
        None,
        gt=0,
        le=5000,
        description="Known portion size in grams"
    )
    context: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional context for analysis"
    )


# Food database manual meal creation requests
class ManualMealItemRequest(BaseModel):
    """Single selected food item with portion to create a manual meal."""
    fdc_id: int = Field(..., description="USDA FDC ID")
    quantity: float = Field(..., gt=0, description="Amount relative to serving unit (e.g., grams)")
    unit: str = Field("g", min_length=1, max_length=20, description="Unit, default grams")


class CreateManualMealFromFoodsRequest(BaseModel):
    """Create a manual meal from selected USDA foods with portions."""
    dish_name: str = Field(..., min_length=1, max_length=200)
    items: list[ManualMealItemRequest] = Field(..., min_items=1)


# Meal Edit Feature Requests
class FoodItemChangeRequest(BaseModel):
    """Request DTO for a single food item change in meal editing."""
    action: Literal["add", "update", "remove"] = Field(..., description="Action to perform: 'add', 'update', or 'remove'")
    id: Optional[str] = Field(None, description="ID of existing food item (required for update/remove)")
    fdc_id: Optional[int] = Field(None, description="USDA FDC ID for new ingredients")
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[float] = Field(None, gt=0, le=10000, description="Quantity amount")
    unit: Optional[str] = Field(None, min_length=1, max_length=20, description="Unit of measurement")
    custom_nutrition: Optional["CustomNutritionRequest"] = Field(None, description="Custom nutrition data for non-USDA ingredients")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "update",
                "id": "123",
                "quantity": 150.0,
                "unit": "g"
            }
        }


class CustomNutritionRequest(BaseModel):
    """Request DTO for custom nutrition data."""
    calories_per_100g: float = Field(..., ge=0, le=1000, description="Calories per 100g")
    protein_per_100g: float = Field(..., ge=0, le=100, description="Protein per 100g in grams")
    carbs_per_100g: float = Field(..., ge=0, le=100, description="Carbohydrates per 100g in grams")
    fat_per_100g: float = Field(..., ge=0, le=100, description="Fat per 100g in grams")

    class Config:
        json_schema_extra = {
            "example": {
                "calories_per_100g": 165.0,
                "protein_per_100g": 31.0,
                "carbs_per_100g": 0.0,
                "fat_per_100g": 3.6,
            }
        }


class EditMealIngredientsRequest(BaseModel):
    """Request DTO for editing meal ingredients."""
    dish_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated meal name")
    food_item_changes: list[FoodItemChangeRequest] = Field(..., min_items=1, description="List of ingredient changes")

    class Config:
        json_schema_extra = {
            "example": {
                "dish_name": "Updated Grilled Chicken Salad",
                "food_item_changes": [
                    {
                        "action": "update",
                        "id": "existing-uuid",
                        "quantity": 200.0,
                        "unit": "g"
                    },
                    {
                        "action": "add",
                        "fdc_id": 168462,
                        "name": "Mixed Greens",
                        "quantity": 100.0,
                        "unit": "g"
                    }
                ]
            }
        }


class AddCustomIngredientRequest(BaseModel):
    """Request DTO for adding custom ingredient to meal."""
    name: str = Field(..., min_length=1, max_length=200, description="Custom ingredient name")
    quantity: float = Field(..., gt=0, le=10000, description="Quantity amount")
    unit: str = Field(..., min_length=1, max_length=20, description="Unit of measurement")
    nutrition: CustomNutritionRequest = Field(..., description="Nutrition data per 100g")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Homemade Vinaigrette",
                "quantity": 30.0,
                "unit": "ml",
                "nutrition": {
                    "calories_per_100g": 400.0,
                    "protein_per_100g": 0.5,
                    "carbs_per_100g": 2.0,
                    "fat_per_100g": 44.0
                }
            }
        }
