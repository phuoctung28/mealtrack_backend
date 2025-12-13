"""
Ingredient recognition request DTOs.
"""
from pydantic import BaseModel, Field


class IngredientRecognitionRequest(BaseModel):
    """Request to recognize an ingredient from an image."""

    image_data: str = Field(
        ...,
        description="Base64 encoded image data (JPEG or PNG)",
        min_length=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        }
