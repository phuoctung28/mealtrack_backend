"""
Response schemas for chat endpoints.
"""
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class FollowUpQuestion(BaseModel):
    """A suggested follow-up question or action."""
    id: str  # Unique identifier for tracking
    text: str  # The question/action text
    type: str  # Type: "question", "recipe", "modify", "alternative"
    metadata: Optional[Dict[str, Any]] = None


class MealSuggestion(BaseModel):
    """A meal suggestion from the AI."""
    name: str
    ingredients: Optional[List[str]] = None
    difficulty: Optional[str] = None  # "easy", "medium", "hard"
    cook_time: Optional[str] = None
    description: Optional[str] = None


class StructuredData(BaseModel):
    """Structured data from AI response (meals, recipes, etc.)."""
    meals: Optional[List[MealSuggestion]] = None
    recipes: Optional[List[Dict[str, Any]]] = None


class MessageResponse(BaseModel):
    """Response for a single message."""
    message_id: str
    thread_id: str
    role: str
    content: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None
    follow_ups: Optional[List[FollowUpQuestion]] = None
    structured_data: Optional[StructuredData] = None


class ThreadResponse(BaseModel):
    """Response for a single thread."""
    thread_id: str
    user_id: str
    title: Optional[str] = None
    status: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    message_count: int = 0
    last_message_at: Optional[str] = None
    messages: Optional[List[MessageResponse]] = None


class ThreadListResponse(BaseModel):
    """Response for list of threads."""
    threads: List[ThreadResponse]
    total_count: int
    limit: int
    offset: int


class SendMessageResponse(BaseModel):
    """Response after sending a message."""
    success: bool
    user_message: MessageResponse
    assistant_message: Optional[MessageResponse] = None

