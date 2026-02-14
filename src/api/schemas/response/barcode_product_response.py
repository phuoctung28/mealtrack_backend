"""
Barcode product response DTOs.
"""
from typing import Optional

from pydantic import BaseModel, Field


class BarcodeProductResponse(BaseModel):
    """Response DTO for barcode product lookup."""

    name: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Product brand")
    barcode: str = Field(..., description="Product barcode")
    calories_100g: Optional[float] = Field(None, description="Calories per 100g")
    protein_100g: Optional[float] = Field(None, description="Protein per 100g")
    carbs_100g: Optional[float] = Field(None, description="Carbohydrates per 100g")
    fat_100g: Optional[float] = Field(None, description="Fat per 100g")
    serving_size: Optional[str] = Field(None, description="Serving size description")
    image_url: Optional[str] = Field(None, description="Product image URL")

    model_config = {"from_attributes": True}
