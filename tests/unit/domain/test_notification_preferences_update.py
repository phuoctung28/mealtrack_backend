"""
Unit tests for NotificationPreferences.update_preferences method.
"""
from datetime import datetime, timezone

import pytest

from src.domain.model.notification.notification_preferences import NotificationPreferences


@pytest.mark.unit
class TestNotificationPreferencesUpdate:
    """Test NotificationPreferences.update_preferences method."""
    
    def test_update_preferences_preserves_last_water_reminder_at(self):
        """Test that updating preferences preserves last_water_reminder_at value."""
        # Arrange: Create preferences with last_water_reminder_at set (timezone-aware UTC)
        original_time = datetime(2025, 12, 7, 10, 30, 0, tzinfo=timezone.utc)
        prefs = NotificationPreferences(
            preferences_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000002",
            last_water_reminder_at=original_time
        )

        # Act: Update meal reminder time (should preserve last_water_reminder_at)
        updated_prefs = prefs.update_preferences(
            breakfast_time_minutes=540  # 9:00 AM
        )

        # Assert: last_water_reminder_at should be preserved
        assert updated_prefs.last_water_reminder_at == original_time
        assert updated_prefs.breakfast_time_minutes == 540
        assert updated_prefs.preferences_id == prefs.preferences_id
        assert updated_prefs.user_id == prefs.user_id
    
    def test_update_preferences_preserves_last_water_reminder_at_when_none(self):
        """Test that updating preferences preserves None value for last_water_reminder_at."""
        # Arrange: Create preferences with last_water_reminder_at as None
        prefs = NotificationPreferences(
            preferences_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000002",
            last_water_reminder_at=None
        )
        
        # Act: Update water reminder interval
        updated_prefs = prefs.update_preferences(
            water_reminder_interval_hours=3
        )
        
        # Assert: last_water_reminder_at should remain None
        assert updated_prefs.last_water_reminder_at is None
        assert updated_prefs.water_reminder_interval_hours == 3
    
    def test_update_preferences_updates_updated_at(self):
        """Test that updating preferences updates the updated_at timestamp."""
        # Arrange (timezone-aware UTC)
        original_updated_at = datetime(2025, 12, 7, 10, 0, 0, tzinfo=timezone.utc)
        prefs = NotificationPreferences(
            preferences_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000002",
            updated_at=original_updated_at
        )

        # Act
        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        updated_prefs = prefs.update_preferences(
            meal_reminders_enabled=False
        )

        # Assert: updated_at should be newer
        assert updated_prefs.updated_at > original_updated_at
        assert updated_prefs.meal_reminders_enabled is False

