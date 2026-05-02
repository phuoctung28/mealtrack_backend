"""Weight entry request schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AddWeightEntryRequest(BaseModel):
    """Request to add a single weight entry."""

    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    recorded_at: datetime = Field(..., description="When the weight was recorded")


class SyncWeightEntriesRequest(BaseModel):
    """Request to bulk sync weight entries from mobile."""

    entries: List[AddWeightEntryRequest] = Field(
        ..., description="List of weight entries to sync"
    )
