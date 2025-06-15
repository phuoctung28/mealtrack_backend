"""
Ingredient DTOs (Data Transfer Objects) for ingredient management APIs.

This module contains:
- Request DTOs for ingredient operations
- Response DTOs for ingredient data
- Collection responses for ingredients
"""

from typing import Optional, List

from pydantic import Field

from app.models import MacrosSchema
from .base import BaseRequest, BaseResponse, TimestampedResponse


# ============================================================================
# Request DTOs
# ============================================================================

class CreateIngredientRequest(BaseRequest):
    """Request DTO for creating a new ingredient."""
    name: str = Field(..., description="Ingredient name")
    description: Optional[str] = Field(None, description="Optional description")
    category: Optional[str] = Field(None, description="Ingredient category")


class UpdateIngredientRequest(BaseRequest):
    """Request DTO for updating an ingredient."""
    name: Optional[str] = Field(None, description="Updated ingredient name")
    description: Optional[str] = Field(None, description="Updated description")
    category: Optional[str] = Field(None, description="Updated category")


class DeleteIngredientRequest(BaseRequest):
    """Request DTO for deleting ingredients."""
    ingredient_ids: List[str] = Field(..., description="List of ingredient IDs to delete")


class IngredientListRequest(BaseRequest):
    """Request DTO for getting ingredient list with filters."""
    category: Optional[str] = Field(None, description="Filter by category")
    search_term: Optional[str] = Field(None, description="Search in name and description")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Number of results to return")


# ============================================================================
# Response DTOs
# ============================================================================

class IngredientResponse(TimestampedResponse):
    """Standard ingredient response DTO."""
    ingredient_id: str
    meal_id: str
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[MacrosSchema] = None


class IngredientCreatedResponse(BaseResponse):
    """Response for successful ingredient creation."""
    ingredient: IngredientResponse
    message: str = "Ingredient added successfully"
    updated_meal_macros: Optional[MacrosSchema] = None


class IngredientUpdatedResponse(BaseResponse):
    """Response for successful ingredient update."""
    ingredient: IngredientResponse
    message: str = "Ingredient updated successfully"
    updated_meal_macros: Optional[MacrosSchema] = None


class IngredientDeletedResponse(BaseResponse):
    """Response for successful ingredient deletion."""
    message: str = "Ingredient deleted successfully"
    deleted_ingredient_id: str
    meal_id: str
    updated_meal_macros: Optional[MacrosSchema] = None


# ============================================================================
# Collection DTOs
# ============================================================================

class IngredientListResponse(BaseResponse):
    """Collection of ingredients for a meal."""
    ingredients: List[IngredientResponse]
    total_count: int
    meal_id: str


# Food-related DTOs for food database routes
class FoodResponse(TimestampedResponse):
    """Response DTO for food items from the food database."""
    food_id: str = Field(..., description="Unique food ID")
    name: str = Field(..., description="Food name")
    brand: Optional[str] = Field(None, description="Brand name if applicable")
    description: Optional[str] = Field(None, description="Food description")
    serving_size: float = Field(..., description="Default serving size")
    serving_unit: str = Field(..., description="Unit for serving size (g, oz, cup, etc.)")
    calories_per_serving: Optional[float] = Field(None, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")
    is_verified: bool = Field(False, description="Whether the food data is verified")


class CreateFoodRequest(BaseRequest):
    """Request DTO for adding a new food to the database."""
    name: str = Field(..., description="Food name")
    brand: Optional[str] = Field(None, description="Brand name")
    description: Optional[str] = Field(None, description="Food description")
    serving_size: float = Field(..., ge=0, description="Default serving size")
    serving_unit: str = Field(..., description="Unit for serving size")
    calories_per_serving: Optional[float] = Field(None, ge=0, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")


class FoodSearchRequest(BaseRequest):
    """Request DTO for searching foods in the database."""
    query: str = Field(..., min_length=1, description="Search query")
    include_ingredients: bool = Field(False, description="Include ingredients in search")
    verified_only: bool = Field(False, description="Only return verified foods")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")


class PaginatedFoodResponse(BaseResponse):
    """Response DTO for paginated food list."""
    foods: List[FoodResponse] = Field(..., description="List of foods")
    total: int = Field(..., description="Total number of foods")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class FoodSearchResponse(BaseResponse):
    """Response DTO for food search results."""
    foods: List[FoodResponse] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of matching foods")
    query: str = Field(..., description="Original search query") 