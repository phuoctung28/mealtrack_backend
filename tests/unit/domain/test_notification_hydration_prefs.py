"""
Unit tests for NotificationPreferences hydration reminders fields.
"""

import pytest

from src.domain.model.notification.notification_preferences import (
    NotificationPreferences,
)


@pytest.mark.unit
class TestNotificationHydrationPrefs:
    """Test hydration_reminders_enabled behaviour on NotificationPreferences."""

    def test_new_instance_has_hydration_reminders_enabled_true_by_default(self):
        """Test that a new NotificationPreferences instance has hydration_reminders_enabled=True."""
        # Arrange / Act
        prefs = NotificationPreferences(
            preferences_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000002",
        )

        # Assert
        assert prefs.hydration_reminders_enabled is True

    def test_create_default_sets_hydration_reminders_enabled_true(self):
        """Test that create_default() initialises hydration_reminders_enabled=True."""
        # Arrange / Act
        prefs = NotificationPreferences.create_default(
            "00000000-0000-0000-0000-000000000003"
        )

        # Assert
        assert prefs.hydration_reminders_enabled is True

    def test_update_preferences_with_hydration_reminders_disabled_returns_false(self):
        """Test that update_preferences(hydration_reminders_enabled=False) disables the flag."""
        # Arrange
        prefs = NotificationPreferences.create_default(
            "00000000-0000-0000-0000-000000000004"
        )

        # Act
        updated = prefs.update_preferences(hydration_reminders_enabled=False)

        # Assert
        assert updated.hydration_reminders_enabled is False
