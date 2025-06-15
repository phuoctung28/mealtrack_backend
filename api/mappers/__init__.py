"""
API Mappers Package

This package contains mapper classes that handle conversion between domain models and DTOs.
Following the Mapper Pattern for clean architecture.

Mappers responsibilities:
- Convert domain models to response DTOs
- Convert request DTOs to domain models  
- Handle data transformation logic
- Keep handlers focused on business orchestration

Structure:
- meal_mapper.py: Meal domain ↔ DTOs conversion
- activity_mapper.py: Activity domain ↔ DTOs conversion
- ingredient_mapper.py: Ingredient domain ↔ DTOs conversion
"""

from .activity_mapper import ActivityMapper
from .ingredient_mapper import IngredientMapper
from .meal_mapper import MealMapper

__all__ = [
    "MealMapper",
    "ActivityMapper", 
    "IngredientMapper"
] 