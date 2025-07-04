from typing import Optional

from pydantic import BaseModel, Field


class ActivityFilterRequest(BaseModel):
    activity_type: Optional[str] = Field(None, description="Filter by activity type")
    start_date: Optional[str] = Field(None, description="Filter activities from this date (ISO format)")
    end_date: Optional[str] = Field(None, description="Filter activities until this date (ISO format)")
    limit: int = Field(20, ge=1, le=100, description="Number of activities to return")
    offset: int = Field(0, ge=0, description="Number of activities to skip")