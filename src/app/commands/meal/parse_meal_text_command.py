"""
Command to parse natural language meal text into structured food items.
"""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Command


@dataclass
class ParseMealTextCommand(Command):
    text: str
    language: str = "en"
    user_id: Optional[str] = None
