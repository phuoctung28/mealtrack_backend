"""
Feature flag request schemas for CRUD operations.
"""
from typing import Optional

from pydantic import BaseModel, Field


class CreateFeatureFlagRequest(BaseModel):
    """Request to create a new feature flag."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Feature flag name")
    enabled: bool = Field(False, description="Initial enabled state")
    description: Optional[str] = Field(None, max_length=500, description="Feature flag description")


class UpdateFeatureFlagRequest(BaseModel):
    """Request to update an existing feature flag."""
    
    enabled: Optional[bool] = Field(None, description="Feature flag enabled state")
    description: Optional[str] = Field(None, max_length=500, description="Feature flag description")