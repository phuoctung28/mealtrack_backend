"""Request schema for custom macro targets."""
from typing import Optional

from pydantic import BaseModel, Field


class UpdateCustomMacrosRequest(BaseModel):
    """Set or clear custom macro targets. Send all null to reset to calculated."""
    protein_g: Optional[float] = Field(None, gt=0, description="Custom protein in grams")
    carbs_g: Optional[float] = Field(None, gt=0, description="Custom carbs in grams")
    fat_g: Optional[float] = Field(None, gt=0, description="Custom fat in grams")
