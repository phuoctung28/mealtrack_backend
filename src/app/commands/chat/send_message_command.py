"""
Command to send a message in a chat thread.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.app.events.base import Command


@dataclass
class SendMessageCommand(Command):
    """Command to send a message in a thread."""
    thread_id: str
    user_id: str  # For authorization
    content: str
    metadata: Optional[Dict[str, Any]] = None

