"""
Command to create a new chat thread.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.app.events.base import Command


@dataclass
class CreateThreadCommand(Command):
    """Command to create a new chat thread."""
    user_id: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

