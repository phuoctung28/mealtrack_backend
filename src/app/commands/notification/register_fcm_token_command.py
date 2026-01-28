"""
Command to register an FCM token for push notifications.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class RegisterFcmTokenCommand(Command):
    """Command to register an FCM token for push notifications."""
    user_id: str
    fcm_token: str
    device_type: str  # 'ios' or 'android'
