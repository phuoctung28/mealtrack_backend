"""
Command for meal image analysis when image is already uploaded.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class AnalyzeMealImageByUrlCommand(Command):
    """
    Command to analyze a pre-uploaded image URL immediately.
    """

    user_id: str
    image_url: str
    public_id: str
    content_type: str
    file_size_bytes: int
    target_date: Optional[date] = None
    language: str = "en"
    user_description: Optional[str] = None
