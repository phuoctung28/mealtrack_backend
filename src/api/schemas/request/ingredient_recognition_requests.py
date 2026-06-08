"""
Ingredient recognition request DTOs.
"""

from pydantic import BaseModel, Field

MAX_IMAGE_BASE64_LENGTH = 7 * 1024 * 1024


class IngredientRecognitionRequest(BaseModel):
    """Request to recognize an ingredient from an image."""

    image_data: str = Field(
        ...,
        description="Base64 encoded image data (JPEG or PNG)",
        min_length=1,
        max_length=MAX_IMAGE_BASE64_LENGTH,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        }
