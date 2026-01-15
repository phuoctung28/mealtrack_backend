"""Timezone utilities for notification scheduling and datetime operations."""
import logging
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime.

    Use this instead of datetime.now() or datetime.utcnow().
    """
    return datetime.now(timezone.utc)


def format_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime as ISO 8601 with UTC timezone suffix.

    Args:
        dt: Datetime to format (can be naive or aware)

    Returns:
        ISO string with timezone, or None if dt is None
    """
    if dt is None:
        return None
    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware UTC.

    Converts naive datetimes by assuming they are UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# Default timezone
DEFAULT_TIMEZONE = "UTC"

# Default quiet hours (for water reminders)
DEFAULT_SLEEP_TIME_MINUTES = 1320  # 10:00 PM
DEFAULT_BREAKFAST_TIME_MINUTES = 480  # 8:00 AM


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


def is_in_quiet_hours(
    local_minutes: int,
    quiet_start: Optional[int],
    quiet_end: Optional[int]
) -> bool:
    """
    Check if local_minutes falls within quiet hours window.

    Handles midnight crossing (quiet_start > quiet_end).
    Uses defaults if values are None.

    Args:
        local_minutes: Current local time in minutes (0-1439)
        quiet_start: Quiet hours start (sleep time) in minutes, or None
        quiet_end: Quiet hours end (breakfast time) in minutes, or None

    Returns:
        True if in quiet hours, False otherwise
    """
    start = quiet_start if quiet_start is not None else DEFAULT_SLEEP_TIME_MINUTES
    end = quiet_end if quiet_end is not None else DEFAULT_BREAKFAST_TIME_MINUTES

    if start > end:
        # Crosses midnight: e.g., 22:00 to 08:00
        return local_minutes >= start or local_minutes < end
    else:
        # Same day: e.g., 01:00 to 05:00
        return start <= local_minutes < end

