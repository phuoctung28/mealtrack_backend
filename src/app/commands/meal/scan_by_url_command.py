"""Command for analyzing a Cloudinary-hosted image via the bytes-download path."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class ScanByUrlCommand(Command):
    """Analyze a Cloudinary-hosted image without sending the URL to the AI provider directly."""

    user_id: str
    image_url: str
    public_id: str
    user_description: Optional[str] = None
    target_date: Optional[date] = None
    language: str = "en"
    scan_mode: str = "scanner"
