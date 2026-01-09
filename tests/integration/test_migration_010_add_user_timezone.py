"""
Integration test for migration 010: Add user timezone and last_water_reminder_at.

This test verifies that:
1. Migration can be applied successfully
2. timezone column exists with default 'UTC'
3. last_water_reminder_at column exists and is nullable
4. Index on timezone column exists
"""
import pytest
from sqlalchemy import inspect

from src.infra.database.models.notification.notification_preferences import NotificationPreferences
from src.infra.database.models.user.user import User


@pytest.mark.integration
class TestMigration010:
    """Test migration 010: Add user timezone and last_water_reminder_at."""
    
    def test_user_timezone_column_exists(self, test_session):
        """Test that timezone column exists in users table."""
        inspector = inspect(test_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('users')}
        
        assert 'timezone' in columns
        assert columns['timezone']['type'].length == 50
        assert columns['timezone']['nullable'] is False
    
    def test_user_timezone_index_exists(self, test_session):
        """Test that index on timezone column exists."""
        inspector = inspect(test_session.bind)
        indexes = inspector.get_indexes('users')
        
        index_names = [idx['name'] for idx in indexes]
        assert 'idx_users_timezone' in index_names
    
    def test_user_timezone_default_value(self, test_session):
        """Test that new users get default timezone 'UTC'."""
        from datetime import datetime
        import uuid
        
        unique_id = str(uuid.uuid4())
        user = User(
            id=unique_id,
            firebase_uid=unique_id,  # firebase_uid column is String(36), UUID is exactly 36 chars
            email=f"test-{unique_id[:8]}@example.com",
            username=f"user-{unique_id[:8]}",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        
        assert user.timezone == 'UTC'
    
    def test_user_timezone_can_be_set(self, test_session):
        """Test that timezone can be set to a valid IANA timezone."""
        from datetime import datetime
        import uuid
        
        unique_id = str(uuid.uuid4())
        user = User(
            id=unique_id,
            firebase_uid=unique_id,  # firebase_uid column is String(36), UUID is exactly 36 chars
            email=f"test-{unique_id[:8]}@example.com",
            username=f"user-{unique_id[:8]}",
            password_hash="dummy_hash",
            timezone="America/Los_Angeles",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        
        assert user.timezone == 'America/Los_Angeles'
    
    def test_notification_preferences_last_water_reminder_at_column_exists(self, test_session):
        """Test that last_water_reminder_at column exists in notification_preferences table."""
        inspector = inspect(test_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('notification_preferences')}
        
        assert 'last_water_reminder_at' in columns
        assert columns['last_water_reminder_at']['nullable'] is True
    
    def test_notification_preferences_last_water_reminder_at_nullable(self, test_session):
        """Test that last_water_reminder_at can be None."""
        import uuid
        
        from src.domain.model.notification import NotificationPreferences as DomainNotificationPreferences
        
        prefs = DomainNotificationPreferences.create_default(str(uuid.uuid4()))
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=prefs.water_reminders_enabled,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=prefs.water_reminder_interval_hours,
            last_water_reminder_at=None,  # Should be nullable
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        test_session.refresh(db_prefs)
        
        assert db_prefs.last_water_reminder_at is None
    
    def test_notification_preferences_last_water_reminder_at_can_be_set(self, test_session):
        """Test that last_water_reminder_at can be set to a datetime."""
        from datetime import datetime
        import uuid
        
        from src.domain.model.notification import NotificationPreferences as DomainNotificationPreferences
        
        # Use a datetime without microseconds since MySQL truncates them
        reminder_time = datetime.now().replace(microsecond=0)
        prefs = DomainNotificationPreferences.create_default(str(uuid.uuid4()))
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=prefs.water_reminders_enabled,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=prefs.water_reminder_interval_hours,
            last_water_reminder_at=reminder_time,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        test_session.refresh(db_prefs)
        
        assert db_prefs.last_water_reminder_at is not None
        # Compare without microseconds as MySQL may truncate them
        assert db_prefs.last_water_reminder_at.replace(microsecond=0) == reminder_time

