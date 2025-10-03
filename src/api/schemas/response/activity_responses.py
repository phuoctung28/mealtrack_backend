"""
Response schemas for activity endpoints.
"""

from pydantic import BaseModel

class MacrosResponse(BaseModel):
    """Macronutrient information."""
    protein: float
    carbs: float
    fat: float

