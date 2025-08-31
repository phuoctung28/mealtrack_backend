"""
Feature flags response schemas for application-level feature control.
"""
from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field


class FeatureFlagsResponse(BaseModel):
    """Response containing feature flags for a specific environment."""
    
    flags: Dict[str, bool] = Field(..., description="Feature flag states")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class IndividualFeatureFlagResponse(BaseModel):
    """Response containing a single feature flag."""
    
    name: str = Field(..., description="Feature flag name")
    enabled: bool = Field(..., description="Feature flag state")
    description: str = Field(None, description="Feature flag description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class FeatureFlagCreatedResponse(BaseModel):
    """Response for successfully created feature flag."""
    
    name: str = Field(..., description="Feature flag name")
    enabled: bool = Field(..., description="Feature flag state")
    description: str = Field(None, description="Feature flag description")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class FeatureFlagUpdatedResponse(BaseModel):
    """Response for successfully updated feature flag."""
    
    name: str = Field(..., description="Feature flag name")
    enabled: bool = Field(..., description="Feature flag state")
    description: str = Field(None, description="Feature flag description")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }