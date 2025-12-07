"""
Unit tests for timezone utilities.
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.domain.services.timezone_utils import (
    get_zone_info,
    utc_to_local_minutes,
    is_valid_timezone,
    DEFAULT_TIMEZONE
)


class TestGetZoneInfo:
    """Test get_zone_info function."""
    
    def test_valid_timezone(self):
        """Test with valid IANA timezone."""
        zone = get_zone_info("America/Los_Angeles")
        assert isinstance(zone, ZoneInfo)
        assert zone.key == "America/Los_Angeles"
    
    def test_invalid_timezone_fallback(self):
        """Test invalid timezone falls back to UTC."""
        zone = get_zone_info("Invalid/Timezone")
        assert isinstance(zone, ZoneInfo)
        assert zone.key == DEFAULT_TIMEZONE
    
    def test_empty_timezone_fallback(self):
        """Test empty timezone falls back to UTC."""
        zone = get_zone_info("")
        assert isinstance(zone, ZoneInfo)
        assert zone.key == DEFAULT_TIMEZONE
    
    def test_none_timezone_fallback(self):
        """Test None timezone falls back to UTC."""
        zone = get_zone_info(None)
        assert isinstance(zone, ZoneInfo)
        assert zone.key == DEFAULT_TIMEZONE


class TestUtcToLocalMinutes:
    """Test utc_to_local_minutes function."""
    
    def test_utc_to_local_minutes_vietnam(self):
        """Test UTC to Vietnam timezone conversion."""
        # 2:00 UTC = 9:00 AM Vietnam (UTC+7)
        utc = datetime(2024, 12, 7, 2, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "Asia/Ho_Chi_Minh")
        assert minutes == 540  # 9:00 AM = 9 * 60 = 540 minutes
    
    def test_utc_to_local_minutes_us_pacific(self):
        """Test UTC to US Pacific timezone conversion."""
        # 17:00 UTC = 9:00 AM Pacific (UTC-8 in December)
        utc = datetime(2024, 12, 7, 17, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "America/Los_Angeles")
        assert minutes == 540  # 9:00 AM = 9 * 60 = 540 minutes
    
    def test_utc_to_local_minutes_us_eastern(self):
        """Test UTC to US Eastern timezone conversion."""
        # 14:00 UTC = 9:00 AM Eastern (UTC-5 in December)
        utc = datetime(2024, 12, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "America/New_York")
        assert minutes == 540  # 9:00 AM = 9 * 60 = 540 minutes
    
    def test_utc_to_local_minutes_midnight(self):
        """Test midnight conversion."""
        utc = datetime(2024, 12, 7, 0, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "UTC")
        assert minutes == 0
    
    def test_utc_to_local_minutes_invalid_timezone(self):
        """Test invalid timezone falls back to UTC."""
        utc = datetime(2024, 12, 7, 12, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "Invalid/Timezone")
        # Should fallback to UTC, so 12:00 UTC = 12:00 UTC = 720 minutes
        assert minutes == 720
    
    def test_dst_handling(self):
        """Test DST transition handling."""
        # March 10, 2024 - US DST starts (spring forward)
        # 9:00 UTC = 5:00 AM EDT (not 4:00 AM EST)
        utc = datetime(2024, 3, 10, 9, 0, tzinfo=ZoneInfo("UTC"))
        minutes = utc_to_local_minutes(utc, "America/New_York")
        assert minutes == 5 * 60  # 5:00 AM


class TestIsValidTimezone:
    """Test is_valid_timezone function."""
    
    def test_valid_timezone(self):
        """Test valid IANA timezone."""
        assert is_valid_timezone("America/Los_Angeles") is True
        assert is_valid_timezone("Asia/Ho_Chi_Minh") is True
        assert is_valid_timezone("Europe/London") is True
        assert is_valid_timezone("UTC") is True
    
    def test_invalid_timezone(self):
        """Test invalid timezone."""
        assert is_valid_timezone("Invalid/Timezone") is False
        assert is_valid_timezone("NotATimezone") is False
    
    def test_empty_timezone(self):
        """Test empty timezone."""
        assert is_valid_timezone("") is False
        assert is_valid_timezone(None) is False

