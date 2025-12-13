"""
Ingredient recognition response DTOs.
"""
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class IngredientCategoryEnum(str, Enum):
    """Category of identified ingredient."""
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    PROTEIN = "protein"
    GRAIN = "grain"
    DAIRY = "dairy"
    SEASONING = "seasoning"
    OTHER = "other"


class IngredientRecognitionResponse(BaseModel):
    """Response from ingredient recognition."""

    name: Optional[str] = Field(
        None,
        description="Identified ingredient name in English (lowercase)"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    category: Optional[IngredientCategoryEnum] = Field(
        None,
        description="Category of the identified ingredient"
    )
    success: bool = Field(
        True,
        description="Whether recognition was successful"
    )
    message: Optional[str] = Field(
        None,
        description="Additional message (e.g., error details)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "chicken breast",
                "confidence": 0.92,
                "category": "protein",
                "success": True,
                "message": None
            }
        }
