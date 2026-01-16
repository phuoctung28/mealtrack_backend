"""
Unit tests for notification query builder - fixed water reminder time logic.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.domain.utils.timezone_utils import utc_to_local_minutes
from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder


class TestFixedWaterReminderQueries:
    """Test suite for find_users_for_fixed_water_reminder functionality."""

    def _setup_mock_db(self, mock_results):
        """Helper to setup mock database with proper query chain."""
        db_mock = MagicMock()
        query_mock = MagicMock()
        join_mock = MagicMock()
        filter_mock = MagicMock()

        # Setup proper chain: db.query().join().filter().all()
        db_mock.query.return_value = query_mock
        query_mock.join.return_value = join_mock
        join_mock.filter.return_value = filter_mock
        filter_mock.all.return_value = mock_results

        return db_mock

    def test_users_at_exact_water_reminder_time(self):
        """Test users matched when local time equals water_reminder_time_minutes."""
        # Mock query results: user at exactly 4:00 PM local (960 minutes)
        mock_results = [
            ("user-1", 960, "UTC"),  # (user_id, water_reminder_time_minutes, timezone)
        ]

        db_mock = self._setup_mock_db(mock_results)

        # Current UTC time that converts to 960 minutes (16:00) in UTC
        current_utc = datetime(2026, 1, 14, 16, 0, 0, tzinfo=timezone.utc)  # 4:00 PM UTC

        # Execute
        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        # Verify
        assert len(result) == 1
        assert "user-1" in result

    def test_timezone_conversion_vietnam_utc_plus_7(self):
        """Test timezone conversion for Vietnam (UTC+7) - 4:00 PM local = 9:00 AM UTC."""
        # User in Vietnam timezone with 4:00 PM reminder (960 minutes)
        mock_results = [
            ("user-vietnam", 960, "Asia/Ho_Chi_Minh"),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # 9:00 AM UTC = 4:00 PM Vietnam (UTC+7)
        current_utc = datetime(2026, 1, 14, 9, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 1
        assert "user-vietnam" in result

    def test_timezone_conversion_us_east_utc_minus_5(self):
        """Test timezone conversion for US Eastern (UTC-5) - 4:00 PM local = 9:00 PM UTC."""
        # User in US Eastern timezone with 4:00 PM reminder
        mock_results = [
            ("user-us-east", 960, "America/New_York"),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # 9:00 PM UTC = 4:00 PM EST (UTC-5)
        current_utc = datetime(2026, 1, 14, 21, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 1
        assert "user-us-east" in result

    def test_water_reminders_disabled_ignored(self):
        """Test users with water_reminders_enabled=False are filtered out by query."""
        # Query should not return disabled users (handled by SQL filter)
        mock_results = []  # Empty because SQL filters out disabled users

        db_mock = self._setup_mock_db(mock_results)

        current_utc = datetime(2026, 1, 14, 16, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 0

    def test_custom_water_reminder_time_not_960(self):
        """Test users with custom water_reminder_time_minutes (e.g., 10:00 AM = 600)."""
        # User wants water reminder at 10:00 AM (600 minutes)
        mock_results = [
            ("user-custom-time", 600, "UTC"),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # 10:00 AM UTC
        current_utc = datetime(2026, 1, 14, 10, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 1
        assert "user-custom-time" in result

    def test_null_timezone_defaults_to_utc(self):
        """Test NULL timezone defaults to UTC in query builder."""
        # User with NULL timezone (should default to UTC)
        mock_results = [
            ("user-null-tz", 960, None),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # 4:00 PM UTC
        current_utc = datetime(2026, 1, 14, 16, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 1
        assert "user-null-tz" in result

    def test_multiple_users_different_timezones_same_local_time(self):
        """Test multiple users in different timezones with same local reminder time."""
        # Three users, all want 4:00 PM local time
        mock_results = [
            ("user-utc", 960, "UTC"),
            ("user-vietnam", 960, "Asia/Ho_Chi_Minh"),
            ("user-us", 960, "America/New_York"),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # 9:00 AM UTC = 4:00 PM Vietnam
        current_utc = datetime(2026, 1, 14, 9, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        # Only Vietnam user should match at this UTC time
        assert len(result) == 1
        assert "user-vietnam" in result

    def test_no_users_matched_wrong_time(self):
        """Test no users matched when current time doesn't match any preference."""
        # User wants 4:00 PM (960 minutes)
        mock_results = [
            ("user-1", 960, "UTC"),
        ]

        db_mock = self._setup_mock_db(mock_results)

        # Current time is 3:00 PM (900 minutes) - doesn't match
        current_utc = datetime(2026, 1, 14, 15, 0, 0, tzinfo=timezone.utc)

        result = ReminderQueryBuilder.find_users_for_fixed_water_reminder(db_mock, current_utc)

        assert len(result) == 0
