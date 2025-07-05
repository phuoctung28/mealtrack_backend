"""
Send conversation message command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class SendConversationMessageCommand(Command):
    """Command to send a message in meal planning conversation."""
    conversation_id: str
    message: str