"""Command for analyzing a Cloudinary-hosted image via the bytes-download path."""

from dataclasses import dataclass
from datetime import date

from src.app.events.base import Command


@dataclass
class ScanByUrlCommand(Command):
    """Analyze a Cloudinary-hosted image without sending the URL to the AI provider directly."""

    user_id: str
    image_url: str
    public_id: str
    user_description: str | None = None
    target_date: date | None = None
    language: str = "en"
    scan_mode: str = "scanner"
    ocr_text_lines: list[str] | None = None
