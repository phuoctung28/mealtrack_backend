"""
Unit tests for NotificationPreferences.update_preferences method.
"""
from datetime import datetime, timezone

import pytest

from src.domain.model.notification.notification_preferences import NotificationPreferences


@pytest.mark.unit
class TestNotificationPreferencesUpdate:
    """Test NotificationPreferences.update_preferences method."""
    
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

