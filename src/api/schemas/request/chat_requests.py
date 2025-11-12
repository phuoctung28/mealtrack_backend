"""
Request schemas for chat endpoints.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CreateThreadRequest(BaseModel):
    """Request to create a new chat thread."""
    title: Optional[str] = Field(None, max_length=255, description="Thread title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class SendMessageRequest(BaseModel):
    """Request to send a message in a thread."""
    content: str = Field(..., min_length=1, max_length=50000, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

