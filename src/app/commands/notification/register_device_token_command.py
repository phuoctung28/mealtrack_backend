"""
Command to register a device token for push notifications.
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class RegisterDeviceTokenCommand:
    """Command to register device token"""
    user_id: str
    device_token: str
    platform: str  # 'ios', 'android', 'web'
    device_info: Dict[str, Any]

