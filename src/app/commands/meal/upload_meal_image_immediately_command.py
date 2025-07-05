"""
Command for immediate meal image upload and analysis.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class UploadMealImageImmediatelyCommand(Command):
    """
    Command to upload and immediately analyze a meal image.
    
    This command combines upload and analysis in a single synchronous operation,
    returning complete nutritional analysis without background processing.
    """
    file_contents: bytes
    content_type: str