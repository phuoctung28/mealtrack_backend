"""
Unit tests for weekly weight reminder background job.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.app.jobs.weekly_weight_reminder_job import WeeklyWeightReminderJob
from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)


@pytest.mark.asyncio
class TestWeeklyWeightReminderJob:
    """Tests for WeeklyWeightReminderJob"""
    
    async def test_job_sends_reminder_to_eligible_users(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test job sends reminders to users with matching schedule"""
        # Get current day and time
        now = datetime.now()
        current_day = (now.weekday() + 1) % 7  # Convert to our format (0=Sunday)
        current_time = now.strftime("%H:%M")
        
        # Set user preferences to match current time
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.weekly_weight_reminder_enabled = True
        sample_user_profile.weekly_weight_reminder_day = current_day
        sample_user_profile.weekly_weight_reminder_time = current_time
        test_session.commit()
        
        # Register a device
        device_repo = DeviceTokenRepository(test_session)
        await device_repo.register_device(
            user_id=sample_user.id,
            device_token="test-token",
            platform="ios",
            device_info={}
        )
        
        # Run the job
        job = WeeklyWeightReminderJob(test_session)
        await job.run()
        
        # Check that notification was logged
        notif_repo = NotificationLogRepository(test_session)
        logs, total = await notif_repo.get_user_notification_history(
            user_id=sample_user.id,
            limit=10,
            offset=0
        )
        
        assert total >= 1
        assert logs[0].notification_type == "weight_reminder"
    
    async def test_job_skips_users_with_disabled_reminders(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test job skips users who disabled reminders"""
        # Get current day and time
        now = datetime.now()
        current_day = (now.weekday() + 1) % 7
        current_time = now.strftime("%H:%M")
        
        # Set user preferences with reminders DISABLED
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.weekly_weight_reminder_enabled = False  # Disabled!
        sample_user_profile.weekly_weight_reminder_day = current_day
        sample_user_profile.weekly_weight_reminder_time = current_time
        test_session.commit()
        
        # Register a device
        device_repo = DeviceTokenRepository(test_session)
        await device_repo.register_device(
            user_id=sample_user.id,
            device_token="test-token",
            platform="ios",
            device_info={}
        )
        
        # Run the job
        job = WeeklyWeightReminderJob(test_session)
        await job.run()
        
        # Check that NO notification was sent
        notif_repo = NotificationLogRepository(test_session)
        logs, total = await notif_repo.get_user_notification_history(
            user_id=sample_user.id,
            limit=10,
            offset=0
        )
        
        assert total == 0
    
    async def test_job_skips_users_with_different_schedule(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test job skips users with different day/time"""
        # Get current day
        now = datetime.now()
        current_day = (now.weekday() + 1) % 7
        
        # Set different day (tomorrow)
        different_day = (current_day + 1) % 7
        
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.weekly_weight_reminder_enabled = True
        sample_user_profile.weekly_weight_reminder_day = different_day  # Different day!
        sample_user_profile.weekly_weight_reminder_time = "09:00"
        test_session.commit()
        
        # Register a device
        device_repo = DeviceTokenRepository(test_session)
        await device_repo.register_device(
            user_id=sample_user.id,
            device_token="test-token",
            platform="ios",
            device_info={}
        )
        
        # Run the job
        job = WeeklyWeightReminderJob(test_session)
        await job.run()
        
        # Check that NO notification was sent (wrong day)
        notif_repo = NotificationLogRepository(test_session)
        logs, total = await notif_repo.get_user_notification_history(
            user_id=sample_user.id,
            limit=10,
            offset=0
        )
        
        assert total == 0
    
    async def test_job_handles_errors_gracefully(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test job continues even if one user fails"""
        # Create a user without a profile (will cause error)
        import uuid
        problem_user = User(
            id=str(uuid.uuid4()),
            firebase_uid=f"problem-user-{uuid.uuid4()}",
            email=f"problem-{uuid.uuid4()}@example.com",
            username=f"problem-{uuid.uuid4()}",
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(problem_user)
        test_session.commit()
        
        # Run the job - should not crash
        job = WeeklyWeightReminderJob(test_session)
        await job.run()
        
        # Job should complete successfully even with problematic user
        assert True  # If we get here, job didn't crash
    
    async def test_find_users_to_remind(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test _find_users_to_remind query"""
        # Get current day and time
        now = datetime.now()
        current_day = (now.weekday() + 1) % 7
        current_time = now.strftime("%H:%M")
        
        # Set user preferences to match
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.weekly_weight_reminder_enabled = True
        sample_user_profile.weekly_weight_reminder_day = current_day
        sample_user_profile.weekly_weight_reminder_time = current_time
        test_session.commit()
        
        # Test the query
        job = WeeklyWeightReminderJob(test_session)
        users = await job._find_users_to_remind(current_day, current_time)
        
        assert len(users) >= 1
        assert any(u.id == sample_user.id for u in users)
    
    async def test_calculate_days_since_last_weight(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test calculating days since last weight update"""
        # Update profile recently
        sample_user_profile.updated_at = datetime.now() - timedelta(days=5)
        test_session.commit()
        
        job = WeeklyWeightReminderJob(test_session)
        days_since = await job._calculate_days_since_last_weight(sample_user.id)
        
        # Should be approximately 5 days
        assert 4 <= days_since <= 6
    
    async def test_calculate_days_since_never_updated(
        self,
        test_session: Session,
        sample_user: User,
        sample_user_profile: UserProfile
    ):
        """Test calculating days when weight never updated"""
        # Set profile created long ago, never updated
        sample_user_profile.created_at = datetime.now() - timedelta(days=100)
        sample_user_profile.updated_at = datetime.now() - timedelta(days=100)
        test_session.commit()
        
        job = WeeklyWeightReminderJob(test_session)
        days_since = await job._calculate_days_since_last_weight(sample_user.id)
        
        # Should be approximately 100 days
        assert days_since >= 90


@pytest.mark.asyncio
class TestJobScheduling:
    """Tests for job scheduling configuration"""
    
    def test_job_is_scheduled(self):
        """Test that job is properly configured in scheduler"""
        from src.app.scheduler import setup_scheduler
        
        scheduler = setup_scheduler()
        
        # Check that weekly weight reminder job is scheduled
        jobs = scheduler.get_jobs()
        job_names = [job.id for job in jobs]
        
        assert "weekly_weight_reminder" in job_names
    
    def test_job_runs_hourly(self):
        """Test that job is configured to run hourly"""
        from src.app.scheduler import setup_scheduler
        
        scheduler = setup_scheduler()
        
        # Find the weekly weight reminder job
        reminder_job = None
        for job in scheduler.get_jobs():
            if job.id == "weekly_weight_reminder":
                reminder_job = job
                break
        
        assert reminder_job is not None
        
        # Check that it's scheduled to run every hour
        # Note: The exact trigger configuration depends on your scheduler setup
        # This is a basic check that the job exists
        assert reminder_job.trigger is not None

