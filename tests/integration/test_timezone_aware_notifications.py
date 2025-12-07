"""
Integration tests for timezone-aware notification queries.
"""
import pytest
import uuid
from datetime import datetime, timezone

from src.domain.model.notification import NotificationPreferences as DomainNotificationPreferences
from src.infra.database.models.user.user import User
from src.infra.database.models.notification.notification_preferences import NotificationPreferences
from src.infra.repositories.notification_repository import NotificationRepository


@pytest.mark.integration
class TestTimezoneAwareMealReminders:
    """Test timezone-aware meal reminder queries."""
    
    def test_find_users_for_meal_reminder_vietnam_timezone(self, test_session):
        """Test meal reminder matching with Vietnam timezone."""
        # Create user in Vietnam timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="Asia/Ho_Chi_Minh",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with breakfast at 9:00 AM (540 minutes)
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.breakfast_time_minutes = 540  # 9:00 AM
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=True,
            water_reminders_enabled=prefs.water_reminders_enabled,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=prefs.water_reminder_interval_hours,
            last_water_reminder_at=prefs.last_water_reminder_at,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: 2:00 UTC = 9:00 AM Vietnam (should match)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 2, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_meal_reminder("breakfast", current_utc)
        
        assert user_id in user_ids
    
    def test_find_users_for_meal_reminder_us_pacific_timezone(self, test_session):
        """Test meal reminder matching with US Pacific timezone."""
        # Create user in US Pacific timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="America/Los_Angeles",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with breakfast at 9:00 AM (540 minutes)
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.breakfast_time_minutes = 540  # 9:00 AM
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=True,
            water_reminders_enabled=prefs.water_reminders_enabled,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=prefs.water_reminder_interval_hours,
            last_water_reminder_at=prefs.last_water_reminder_at,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: 17:00 UTC = 9:00 AM Pacific (should match)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 17, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_meal_reminder("breakfast", current_utc)
        
        assert user_id in user_ids
    
    def test_find_users_for_meal_reminder_different_timezones_same_preference(self, test_session):
        """Test that same preference time in different timezones triggers at different UTC times."""
        # Create user 1 in Vietnam
        user1_id = str(uuid.uuid4())
        user1 = User(
            id=user1_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="Asia/Ho_Chi_Minh",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user1)
        
        # Create user 2 in US Pacific
        user2_id = str(uuid.uuid4())
        user2 = User(
            id=user2_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="America/Los_Angeles",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user2)
        test_session.commit()
        
        # Both want breakfast at 9:00 AM local time
        for uid in [user1_id, user2_id]:
            prefs = DomainNotificationPreferences.create_default(uid)
            prefs.breakfast_time_minutes = 540
            db_prefs = NotificationPreferences(
                id=prefs.preferences_id,
                user_id=prefs.user_id,
                meal_reminders_enabled=True,
                water_reminders_enabled=prefs.water_reminders_enabled,
                sleep_reminders_enabled=prefs.sleep_reminders_enabled,
                progress_notifications_enabled=prefs.progress_notifications_enabled,
                reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
                breakfast_time_minutes=prefs.breakfast_time_minutes,
                lunch_time_minutes=prefs.lunch_time_minutes,
                dinner_time_minutes=prefs.dinner_time_minutes,
                water_reminder_interval_hours=prefs.water_reminder_interval_hours,
                last_water_reminder_at=prefs.last_water_reminder_at,
                sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
                created_at=prefs.created_at,
                updated_at=prefs.updated_at
            )
            test_session.add(db_prefs)
        test_session.commit()
        
        repository = NotificationRepository(db=test_session)
        
        # 2:00 UTC = 9:00 AM Vietnam (user1 should match)
        current_utc = datetime(2024, 12, 7, 2, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_meal_reminder("breakfast", current_utc)
        assert user1_id in user_ids
        assert user2_id not in user_ids
        
        # 17:00 UTC = 9:00 AM Pacific (user2 should match)
        current_utc = datetime(2024, 12, 7, 17, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_meal_reminder("breakfast", current_utc)
        assert user1_id not in user_ids
        assert user2_id in user_ids


@pytest.mark.integration
class TestTimezoneAwareSleepReminders:
    """Test timezone-aware sleep reminder queries."""
    
    def test_find_users_for_sleep_reminder_timezone_aware(self, test_session):
        """Test sleep reminder matching with timezone conversion."""
        # Create user in Vietnam timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="Asia/Ho_Chi_Minh",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with sleep reminder at 10:00 PM (1320 minutes)
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.sleep_reminder_time_minutes = 1320  # 10:00 PM
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=prefs.water_reminders_enabled,
            sleep_reminders_enabled=True,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=prefs.water_reminder_interval_hours,
            last_water_reminder_at=prefs.last_water_reminder_at,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: 15:00 UTC = 10:00 PM Vietnam (should match)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 15, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_sleep_reminder(current_utc)
        
        assert user_id in user_ids


@pytest.mark.integration
class TestWaterReminderInterval:
    """Test water reminder interval logic."""
    
    def test_find_users_for_water_reminder_no_previous_reminder(self, test_session):
        """Test water reminder for users who never received one."""
        # Create user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with water reminders enabled, no previous reminder
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.water_reminders_enabled = True
        prefs.water_reminder_interval_hours = 2
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: Should match since never sent
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        
        assert user_id in user_ids
    
    def test_find_users_for_water_reminder_interval_passed(self, test_session):
        """Test water reminder when interval has passed."""
        # Create user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with last reminder 3 hours ago (interval is 2 hours)
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.water_reminders_enabled = True
        prefs.water_reminder_interval_hours = 2
        last_reminder = datetime(2024, 12, 7, 9, 0, tzinfo=timezone.utc)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=last_reminder,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: Current time is 12:00, last was 9:00 (3 hours ago, interval is 2 hours)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        
        assert user_id in user_ids
    
    def test_find_users_for_water_reminder_interval_not_passed(self, test_session):
        """Test water reminder when interval has not passed."""
        # Create user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences with last reminder 1 hour ago (interval is 2 hours)
        prefs = DomainNotificationPreferences.create_default(user_id)
        prefs.water_reminders_enabled = True
        prefs.water_reminder_interval_hours = 2
        last_reminder = datetime(2024, 12, 7, 11, 0, tzinfo=timezone.utc)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=prefs.breakfast_time_minutes,
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=last_reminder,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test: Current time is 12:00, last was 11:00 (1 hour ago, interval is 2 hours)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        
        assert user_id not in user_ids
    
    def test_update_last_water_reminder(self, test_session):
        """Test updating last water reminder timestamp."""
        # Create user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Create notification preferences
        prefs = DomainNotificationPreferences.create_default(user_id)
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
            last_water_reminder_at=None,
            sleep_reminder_time_minutes=prefs.sleep_reminder_time_minutes,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()
        
        # Test update
        repository = NotificationRepository(db=test_session)
        sent_at = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        result = repository.update_last_water_reminder(user_id, sent_at)
        
        assert result is True
        test_session.refresh(db_prefs)
        assert db_prefs.last_water_reminder_at == sent_at


@pytest.mark.integration
class TestWaterReminderQuietHours:
    """Integration tests for water reminder quiet hours."""

    def test_skip_water_reminder_during_quiet_hours(self, test_session):
        """Water reminder skipped when user is in quiet hours (local 23:00)."""
        # Create user in UTC timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()

        # Create notification preferences with sleep=22:00, breakfast=08:00
        prefs = DomainNotificationPreferences.create_default(user_id)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=480,  # 08:00
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,  # Never sent
            sleep_reminder_time_minutes=1320,  # 22:00
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()

        # Test: 23:00 UTC (in quiet hours for UTC user)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 23, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)

        assert user_id not in user_ids

    def test_send_water_reminder_outside_quiet_hours(self, test_session):
        """Water reminder sent when user is outside quiet hours (local 12:00)."""
        # Create user in UTC timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()

        # Create notification preferences with sleep=22:00, breakfast=08:00
        prefs = DomainNotificationPreferences.create_default(user_id)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=480,  # 08:00
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,  # Never sent
            sleep_reminder_time_minutes=1320,  # 22:00
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()

        # Test: 12:00 UTC (outside quiet hours for UTC user)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)

        assert user_id in user_ids

    def test_quiet_hours_respects_timezone(self, test_session):
        """Quiet hours calculation respects user timezone."""
        # Create user in Vietnam timezone (UTC+7)
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="Asia/Ho_Chi_Minh",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()

        # Create notification preferences with sleep=22:00, breakfast=08:00 (local VN time)
        prefs = DomainNotificationPreferences.create_default(user_id)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=480,  # 08:00 VN
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,
            sleep_reminder_time_minutes=1320,  # 22:00 VN
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()

        repository = NotificationRepository(db=test_session)

        # Test: 15:00 UTC = 22:00 VN (just entered quiet hours) → NOT returned
        current_utc = datetime(2024, 12, 7, 15, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        assert user_id not in user_ids

        # Test: 05:00 UTC = 12:00 VN (noon, outside quiet hours) → returned
        current_utc = datetime(2024, 12, 7, 5, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        assert user_id in user_ids

    def test_quiet_hours_early_morning(self, test_session):
        """Water reminder skipped during early morning quiet hours."""
        # Create user in UTC timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()

        # Create notification preferences with sleep=22:00, breakfast=08:00
        prefs = DomainNotificationPreferences.create_default(user_id)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=480,  # 08:00
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,
            sleep_reminder_time_minutes=1320,  # 22:00
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()

        # Test: 03:00 UTC (early morning, in quiet hours)
        repository = NotificationRepository(db=test_session)
        current_utc = datetime(2024, 12, 7, 3, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)

        assert user_id not in user_ids

    def test_quiet_hours_uses_defaults_when_none(self, test_session):
        """Quiet hours uses defaults (22:00-08:00) when user has no prefs set."""
        # Create user in UTC timezone
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            firebase_uid=f"test-fb-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            username=f"user-{uuid.uuid4()}",
            password_hash="dummy_hash",
            timezone="UTC",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()

        # Create notification preferences with sleep and breakfast time as None
        prefs = DomainNotificationPreferences.create_default(user_id)
        db_prefs = NotificationPreferences(
            id=prefs.preferences_id,
            user_id=prefs.user_id,
            meal_reminders_enabled=prefs.meal_reminders_enabled,
            water_reminders_enabled=True,
            sleep_reminders_enabled=prefs.sleep_reminders_enabled,
            progress_notifications_enabled=prefs.progress_notifications_enabled,
            reengagement_notifications_enabled=prefs.reengagement_notifications_enabled,
            breakfast_time_minutes=None,  # Will use default 08:00
            lunch_time_minutes=prefs.lunch_time_minutes,
            dinner_time_minutes=prefs.dinner_time_minutes,
            water_reminder_interval_hours=2,
            last_water_reminder_at=None,
            sleep_reminder_time_minutes=None,  # Will use default 22:00
            created_at=prefs.created_at,
            updated_at=prefs.updated_at
        )
        test_session.add(db_prefs)
        test_session.commit()

        repository = NotificationRepository(db=test_session)

        # 23:00 UTC should be in quiet hours (default 22:00-08:00)
        current_utc = datetime(2024, 12, 7, 23, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        assert user_id not in user_ids

        # 12:00 UTC should be outside quiet hours
        current_utc = datetime(2024, 12, 7, 12, 0, tzinfo=timezone.utc)
        user_ids = repository.find_users_for_water_reminder(current_utc)
        assert user_id in user_ids

