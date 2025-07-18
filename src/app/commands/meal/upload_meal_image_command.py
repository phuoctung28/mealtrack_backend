"""
Upload meal image command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class UploadMealImageCommand(Command):
    """Command to upload and analyze a meal image."""
    file_contents: bytes
    content_type: str