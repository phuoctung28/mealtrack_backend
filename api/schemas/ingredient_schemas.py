from pydantic import BaseModel, Field
from typing import Optional, List
from .food_schemas import MacrosSchema, MicrosSchema

class CreateIngredientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: float = Field(..., gt=0, description="Quantity of ingredient")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosSchema] = Field(None, description="Macronutrients")
    micros: Optional[MicrosSchema] = Field(None, description="Micronutrients")

class UpdateIngredientRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity of ingredient")
    unit: Optional[str] = Field(None, min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosSchema] = Field(None, description="Macronutrients")
    micros: Optional[MicrosSchema] = Field(None, description="Micronutrients")

class IngredientResponse(BaseModel):
    ingredient_id: str
    food_id: str
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[MacrosSchema] = None
    micros: Optional[MicrosSchema] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class IngredientListResponse(BaseModel):
    ingredients: List[IngredientResponse]
    total_count: int
    food_id: str

class IngredientCreatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient added successfully"
    updated_food_macros: Optional[MacrosSchema] = None  # Updated macros for the parent food

class IngredientUpdatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient updated successfully"
    updated_food_macros: Optional[MacrosSchema] = None  # Updated macros for the parent food

class IngredientDeletedResponse(BaseModel):
    message: str = "Ingredient deleted successfully"
    deleted_ingredient_id: str
    updated_food_macros: Optional[MacrosSchema] = None  # Updated macros for the parent food 