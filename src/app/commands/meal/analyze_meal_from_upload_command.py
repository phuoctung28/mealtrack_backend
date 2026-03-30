"""
Command for analyzing a meal image that has already been uploaded to Cloudinary.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class AnalyzeMealFromUploadCommand(Command):
    user_id: str
    cloudinary_url: str
    cloudinary_public_id: str
    target_date: Optional[date] = None
    user_description: Optional[str] = None

