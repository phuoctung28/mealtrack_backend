"""
Pydantic schemas for structured meal generation output.
Used with LangChain's with_structured_output() for guaranteed valid responses.
"""
from typing import List
from pydantic import BaseModel, Field


class MealNamesResponse(BaseModel):
    """Phase 1: Response containing 3 diverse meal names."""
    
    meal_names: List[str] = Field(
        description="List of exactly 3 diverse, concise meal names (max 60 chars each) with different cuisines and cooking styles",
        min_length=3,
        max_length=3
    )
    
    # B2 FIX: Validate each meal name is reasonably short
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate individual meal name lengths
        for i, name in enumerate(self.meal_names):
            if len(name) > 60:
                self.meal_names[i] = name[:57] + "..."  # Truncate if too long


class IngredientItem(BaseModel):
    """Single ingredient with amount and unit."""
    
    name: str = Field(description="Ingredient name (e.g., 'chicken breast', 'broccoli')")
    amount: float = Field(description="Quantity amount (e.g., 200, 1.5)", gt=0)
    unit: str = Field(description="Unit of measurement (e.g., 'g', 'ml', 'tbsp', 'tsp', 'cup')")


class RecipeStepItem(BaseModel):
    """Single recipe step with instruction and duration."""
    
    step: int = Field(description="Step number (1, 2, 3, ...)", ge=1)
    instruction: str = Field(description="Clear, actionable instruction")
    duration_minutes: int = Field(description="Time in minutes for this step", ge=0)


class RecipeDetailsResponse(BaseModel):
    """Phase 2: Complete recipe details for a meal."""
    
    description: str = Field(description="Brief, appetizing description of the meal")
    ingredients: List[IngredientItem] = Field(
        description="List of 4-6 ingredients with exact amounts",
        min_length=4,
        max_length=6
    )
    recipe_steps: List[RecipeStepItem] = Field(
        description="List of 3-4 recipe steps with instructions and durations",
        min_length=3,
        max_length=4
    )
    prep_time_minutes: int = Field(
        description="Total preparation and cooking time in minutes",
        ge=5,
        le=120
    )
