"""
Meal-related request DTOs.
"""
from typing import Optional

from pydantic import BaseModel, Field


class CreateManualMealFromFoodsRequest(BaseModel):
    """Create a manual meal from selected USDA foods with portions."""
    dish_name: str = Field(..., min_length=1, max_length=200)
    items: list[ManualMealItemRequest] = Field(..., min_items=1)

# Meal Edit Feature Requests
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

