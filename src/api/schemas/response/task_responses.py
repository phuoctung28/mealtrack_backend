"""Response schemas for async task creation/status polling."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskCreatedResponse(BaseModel):
    task_id: str = Field(..., description="Task/job identifier")
    status: str = Field(..., description="Initial task status")
    poll_url: str = Field(..., description="Relative URL to poll for status/result")
    message: Optional[str] = Field(None, description="Human-friendly message")


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Task/job identifier")
    status: str = Field(..., description="Task status")
    result: Optional[Any] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error details if failed")
    created_at: Optional[datetime] = Field(None, description="Job creation time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")

