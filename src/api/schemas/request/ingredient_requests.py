from typing import Optional

from pydantic import BaseModel, Field

from ..response import MacrosResponse


class CreateIngredientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: float = Field(..., gt=0, description="Quantity of ingredient")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosResponse] = Field(None, description="Macronutrients")

class UpdateIngredientRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity of ingredient")
    unit: Optional[str] = Field(None, min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosResponse] = Field(None, description="Macronutrients")