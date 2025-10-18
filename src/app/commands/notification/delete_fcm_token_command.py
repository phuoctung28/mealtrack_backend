"""
Command to delete an FCM token.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteFcmTokenCommand(Command):
    """Command to delete an FCM token."""
    user_id: str
    fcm_token: str
