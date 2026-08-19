"""Request bodies for catalog meal logging."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class LogCatalogMealRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=160)
    meal_date: date
    meal_type: MealType
