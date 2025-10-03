from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from ..common.meal_plan_enums import (
    DietaryPreferenceSchema
)


class ReplaceMealRequest(BaseModel):
    date: date
    meal_id: str
    dietary_preferences: Optional[List[DietaryPreferenceSchema]] = None
    exclude_ingredients: Optional[List[str]] = None
    preferred_cuisine: Optional[str] = None

