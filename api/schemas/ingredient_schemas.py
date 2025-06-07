from pydantic import BaseModel, Field
from typing import Optional, List
from .meal_schemas import MacrosSchema

class CreateIngredientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    quantity: float = Field(..., gt=0, description="Quantity of ingredient")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosSchema] = Field(None, description="Macronutrients")

class UpdateIngredientRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Ingredient name")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity of ingredient")
    unit: Optional[str] = Field(None, min_length=1, max_length=50, description="Unit of measurement")
    calories: Optional[float] = Field(None, ge=0, description="Calories")
    macros: Optional[MacrosSchema] = Field(None, description="Macronutrients")

class IngredientResponse(BaseModel):
    ingredient_id: str
    meal_id: str
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[MacrosSchema] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class IngredientListResponse(BaseModel):
    ingredients: List[IngredientResponse]
    total_count: int
    meal_id: str

class IngredientCreatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient added successfully"
    updated_meal_macros: Optional[MacrosSchema] = None  # Updated macros for the parent meal

class IngredientUpdatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient updated successfully"
    updated_meal_macros: Optional[MacrosSchema] = None  # Updated macros for the parent meal

class IngredientDeletedResponse(BaseModel):
    message: str = "Ingredient deleted successfully"
    deleted_ingredient_id: str
    meal_id: str
    updated_meal_macros: Optional[MacrosSchema] = None  # Updated macros for the parent meal 