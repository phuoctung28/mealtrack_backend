from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ActivityResponse(BaseModel):
    activity_id: str
    user_id: Optional[str] = None
    activity_type: str
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

class ActivitiesListResponse(BaseModel):
    activities: List[ActivityResponse]
    total_count: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int

class ActivityFilterRequest(BaseModel):
    activity_type: Optional[str] = Field(None, description="Filter by activity type")
    start_date: Optional[str] = Field(None, description="Filter activities from this date (ISO format)")
    end_date: Optional[str] = Field(None, description="Filter activities until this date (ISO format)")
    limit: int = Field(20, ge=1, le=100, description="Number of activities to return")
    offset: int = Field(0, ge=0, description="Number of activities to skip") 