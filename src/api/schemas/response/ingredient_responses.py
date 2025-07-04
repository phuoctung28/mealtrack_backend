from typing import Optional, List

from pydantic import BaseModel

from .meal_responses import MacrosResponse


class IngredientResponse(BaseModel):
    ingredient_id: str
    meal_id: str
    name: str
    quantity: float
    unit: str
    calories: Optional[float] = None
    macros: Optional[MacrosResponse] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class IngredientListResponse(BaseModel):
    ingredients: List[IngredientResponse]
    total_count: int
    meal_id: str

class IngredientCreatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient added successfully"
    updated_meal_macros: Optional[MacrosResponse] = None  # Updated macros for the parent meal

class IngredientUpdatedResponse(BaseModel):
    ingredient: IngredientResponse
    message: str = "Ingredient updated successfully"
    updated_meal_macros: Optional[MacrosResponse] = None  # Updated macros for the parent meal

class IngredientDeletedResponse(BaseModel):
    message: str = "Ingredient deleted successfully"
    deleted_ingredient_id: str
    meal_id: str
    updated_meal_macros: Optional[MacrosResponse] = None  # Updated macros for the parent meal