"""
Meal-related request DTOs.
"""
import warnings
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, field_validator


class ParseMealTextRequest(BaseModel):
    """Request DTO for parsing meal text descriptions."""
    text: str = Field(..., min_length=1, max_length=500, description="Natural language food description")
    current_items: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Current meal items for refinement (when user is editing an existing meal)"
    )


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
    language: str = Field(
        default="en",
        description="ISO 639-1 language code for translated results (en, vi, es, fr, de, ja, zh)"
    )

    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validate language code and fallback to 'en' if invalid."""
        valid_languages = {"en", "vi", "es", "fr", "de", "ja", "zh"}
        normalized = v.lower().strip()
        if normalized not in valid_languages:
            warnings.warn(
                f"Unsupported language code '{v}', falling back to 'en'",
                UserWarning,
                stacklevel=2,
            )
            return "en"
        return normalized


# Food database manual meal creation requests
class ManualMealItemRequest(BaseModel):
    """Single selected food item with portion to create a manual meal.

    Supports both USDA foods (via fdc_id) and custom foods (via name + custom_nutrition).
    """
    fdc_id: Optional[int] = Field(None, description="USDA FDC ID (required for USDA foods)")
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Food name (required for custom foods)")
    quantity: float = Field(..., gt=0, description="Amount relative to serving unit (e.g., grams)")
    unit: str = Field("g", min_length=1, max_length=20, description="Unit, default grams")
    custom_nutrition: Optional["CustomNutritionRequest"] = Field(
        None, description="Custom nutrition data for non-USDA foods (e.g., barcode products)"
    )


class CreateManualMealFromFoodsRequest(BaseModel):
    """Create a manual meal from selected USDA foods with portions."""
    dish_name: str = Field(..., min_length=1, max_length=200)
    items: list[ManualMealItemRequest] = Field(..., min_items=1)
    meal_type: Optional[str] = Field(None, description="Meal type: breakfast, lunch, dinner, or snack")
    target_date: Optional[str] = Field(None, description="Target date in YYYY-MM-DD format for meal association")
    source: Optional[str] = Field(None, description="Meal source: scanner, prompt, food_search, manual")
    emoji: Optional[str] = Field(None, description="AI-assigned dish emoji")


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
    """Request DTO for custom nutrition data.

    Calories always derived from macros: P*4 + C*4 + F*9.
    """
    protein_per_100g: float = Field(..., ge=0, le=100, description="Protein per 100g in grams")
    carbs_per_100g: float = Field(..., ge=0, le=100, description="Carbohydrates per 100g in grams")
    fat_per_100g: float = Field(..., ge=0, le=100, description="Fat per 100g in grams")

    @property
    def calories_per_100g(self) -> float:
        """Derive calories from macros: P*4 + C*4 + F*9."""
        return round(self.protein_per_100g * 4 + self.carbs_per_100g * 4 + self.fat_per_100g * 9, 2)

    class Config:
        json_schema_extra = {
            "example": {
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
                    "protein_per_100g": 0.5,
                    "carbs_per_100g": 2.0,
                    "fat_per_100g": 44.0
                }
            }
        }
