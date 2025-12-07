"""Timezone utilities for notification scheduling."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

# Default timezone
DEFAULT_TIMEZONE = "UTC"


def get_zone_info(timezone_str: str) -> ZoneInfo:
    """
    Get ZoneInfo for timezone string with fallback to UTC.

    Args:
        timezone_str: IANA timezone identifier (e.g., "America/Los_Angeles")

    Returns:
        ZoneInfo object, defaults to UTC if timezone invalid
    """
    if not timezone_str:
        return ZoneInfo(DEFAULT_TIMEZONE)

    try:
        return ZoneInfo(timezone_str)
    except ZoneInfoNotFoundError:
        logger.warning(f"Invalid timezone '{timezone_str}', falling back to UTC")
        return ZoneInfo(DEFAULT_TIMEZONE)


def utc_to_local_minutes(utc_time: datetime, timezone_str: str) -> int:
    """
    Convert UTC datetime to local time minutes from midnight.

    Args:
        utc_time: UTC datetime (must be timezone-aware)
        timezone_str: IANA timezone identifier

    Returns:
        Minutes from midnight in user's local time (0-1439)
    """
    zone_info = get_zone_info(timezone_str)
    local_time = utc_time.astimezone(zone_info)
    return local_time.hour * 60 + local_time.minute


def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if timezone string is valid IANA identifier.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        True if valid IANA timezone
    """
    if not timezone_str:
        return False

    try:
        ZoneInfo(timezone_str)
        return True
    except ZoneInfoNotFoundError:
        return False

