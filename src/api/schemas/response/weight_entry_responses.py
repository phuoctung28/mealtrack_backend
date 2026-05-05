"""Weight entry response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WeightEntryResponse(BaseModel):
    """Response for a single weight entry."""

    id: str = Field(..., description="Entry ID")
    weight_kg: float = Field(..., description="Weight in kilograms")
    recorded_at: datetime = Field(..., description="When the weight was recorded")
    created_at: Optional[datetime] = Field(None, description="When entry was created")


class WeightEntriesListResponse(BaseModel):
    """Response containing list of weight entries."""

    entries: List[WeightEntryResponse] = Field(..., description="Weight entries")
    count: int = Field(..., description="Total count of entries")


class SyncWeightEntriesResponse(BaseModel):
    """Response from bulk sync operation."""

    synced_count: int = Field(..., description="Number of entries synced")
    message: str = Field(..., description="Operation result message")
