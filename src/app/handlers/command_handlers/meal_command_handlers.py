"""
DEPRECATED: This file is kept for backward compatibility only.

All handlers have been moved to individual files:
- UploadMealImageCommandHandler → upload_meal_image_handler.py
- RecalculateMealNutritionCommandHandler → recalculate_meal_nutrition_handler.py
- EditMealCommandHandler → edit_meal_handler.py
- AddCustomIngredientCommandHandler → add_custom_ingredient_handler.py
- DeleteMealCommandHandler → delete_meal_handler.py

Please import handlers from their individual files or from the command_handlers module:
    from src.app.handlers.command_handlers import EditMealCommandHandler
"""

from .add_custom_ingredient_handler import AddCustomIngredientCommandHandler
from .delete_meal_handler import DeleteMealCommandHandler
from .edit_meal_handler import EditMealCommandHandler
from .recalculate_meal_nutrition_handler import RecalculateMealNutritionCommandHandler
# Re-export all handlers for backward compatibility
from .upload_meal_image_handler import UploadMealImageCommandHandler

__all__ = [
    "UploadMealImageCommandHandler",
    "RecalculateMealNutritionCommandHandler",
    "EditMealCommandHandler",
    "AddCustomIngredientCommandHandler",
    "DeleteMealCommandHandler",
]
