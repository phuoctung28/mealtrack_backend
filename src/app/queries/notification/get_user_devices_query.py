"""
Query to get user's registered devices.
"""
from dataclasses import dataclass


@dataclass
class GetUserDevicesQuery:
    """Query to get user devices"""
    user_id: str
    active_only: bool = True

