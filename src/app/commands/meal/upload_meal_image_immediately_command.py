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
    file_contents: bytes
    content_type: str
    target_date: Optional[date] = None
    language: str = "en"
    user_description: Optional[str] = None  # User-provided context for better accuracy
    timezone: Optional[str] = None  # IANA timezone (e.g., "Asia/Saigon") for accurate meal type detection