"""
Command for immediate meal image upload and analysis.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class UploadMealImageImmediatelyCommand(Command):
    """
    Command to upload and immediately analyze a meal image.

    This command combines upload and analysis in a single synchronous operation,
    returning complete nutritional analysis without background processing.
    """
    user_id: str
    file_contents: Optional[bytes] = None
    content_type: Optional[str] = None
    meal_id: Optional[str] = None
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    target_date: Optional[date] = None
    language: str = "en"
    user_description: Optional[str] = None  # User-provided context for better accuracy