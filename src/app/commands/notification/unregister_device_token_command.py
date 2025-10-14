"""
Command to unregister a device token.
"""
from dataclasses import dataclass


@dataclass
class UnregisterDeviceTokenCommand:
    """Command to unregister device token"""
    user_id: str
    device_id: str

