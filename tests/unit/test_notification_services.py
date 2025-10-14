"""
Unit tests for notification services.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.app.services.notification_preference_service import NotificationPreferenceService
from src.app.services.push_notification_service import PushNotificationService
from src.app.services.email_notification_service import EmailNotificationService
from src.app.services.notification_dispatch_service import NotificationDispatchService
from src.domain.model.notification import Notification, NotificationPreferences
from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)


@pytest.mark.asyncio
class TestNotificationPreferenceService:
    """Tests for NotificationPreferenceService"""
    
    async def test_get_preferences_returns_user_profile_preferences(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test getting notification preferences from user profile"""
        service = NotificationPreferenceService(test_session)
        
        # Update preferences
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.email_notifications_enabled = False
        sample_user_profile.weekly_weight_reminder_enabled = True
        sample_user_profile.weekly_weight_reminder_day = 1  # Monday
        sample_user_profile.weekly_weight_reminder_time = "10:00"
        test_session.commit()
        
        preferences = await service.get_preferences(sample_user.id)
        
        assert preferences is not None
        assert preferences.notifications_enabled is True
        assert preferences.push_notifications_enabled is True
        assert preferences.weekly_weight_reminder_day == 1
        assert preferences.weekly_weight_reminder_time == "10:00"
    
    async def test_update_preferences(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test updating notification preferences"""
        service = NotificationPreferenceService(test_session)
        
        new_prefs = NotificationPreferences(
            notifications_enabled=True,
            push_notifications_enabled=False,
            email_notifications_enabled=True,
            weekly_weight_reminder_enabled=True,
            weekly_weight_reminder_day=5,  # Friday
            weekly_weight_reminder_time="08:00"
        )
        
        updated = await service.update_preferences(sample_user.id, new_prefs)
        
        assert updated is not None
        assert updated.push_notifications_enabled is False
        assert updated.email_notifications_enabled is True
        assert updated.weekly_weight_reminder_day == 5
        assert updated.weekly_weight_reminder_time == "08:00"
    
    async def test_can_send_notification_returns_true_when_enabled(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test can_send_notification returns True when enabled"""
        service = NotificationPreferenceService(test_session)
        
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        test_session.commit()
        
        can_send = await service.can_send_notification(sample_user.id, "push")
        
        assert can_send is True
    
    async def test_can_send_notification_returns_false_when_disabled(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test can_send_notification returns False when disabled"""
        service = NotificationPreferenceService(test_session)
        
        sample_user_profile.notifications_enabled = False
        test_session.commit()
        
        can_send = await service.can_send_notification(sample_user.id, "push")
        
        assert can_send is False


@pytest.mark.asyncio
class TestPushNotificationService:
    """Tests for PushNotificationService"""
    
    async def test_send_push_notification_creates_log(
        self, test_session: Session, sample_user: User
    ):
        """Test sending push notification creates log"""
        device_repo = DeviceTokenRepository(test_session)
        notif_repo = NotificationLogRepository(test_session)
        
        # Register device
        await device_repo.register_device(
            user_id=sample_user.id,
            device_token="test-fcm-token",
            platform="ios",
            device_info={}
        )
        
        # Create service without FCM credentials (will skip actual sending)
        service = PushNotificationService(
            device_repository=device_repo,
            notification_repository=notif_repo,
            fcm_credentials_path=None  # No credentials - graceful degradation
        )
        
        notification = Notification(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test Notification",
            body="Test body",
            data={"test": True}
        )
        
        notification_ids = await service.send_push_notification(
            sample_user.id,
            notification
        )
        
        # Should create log even without FCM
        assert len(notification_ids) == 1
        
        # Verify log was created
        logs, total = await notif_repo.get_user_notification_history(
            user_id=sample_user.id,
            limit=10,
            offset=0
        )
        assert total == 1
        assert logs[0].notification_type == "weight_reminder"
    
    async def test_send_push_notification_no_devices(
        self, test_session: Session, sample_user: User
    ):
        """Test sending push notification with no registered devices"""
        device_repo = DeviceTokenRepository(test_session)
        notif_repo = NotificationLogRepository(test_session)
        
        service = PushNotificationService(
            device_repository=device_repo,
            notification_repository=notif_repo,
            fcm_credentials_path=None
        )
        
        notification = Notification(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test",
            body="Test",
            data={}
        )
        
        notification_ids = await service.send_push_notification(
            sample_user.id,
            notification
        )
        
        # Should return empty list when no devices
        assert len(notification_ids) == 0


@pytest.mark.asyncio
class TestEmailNotificationService:
    """Tests for EmailNotificationService"""
    
    async def test_send_email_without_smtp_config(
        self, test_session: Session, sample_user: User
    ):
        """Test sending email without SMTP configuration"""
        notif_repo = NotificationLogRepository(test_session)
        
        # Create service without SMTP config (will skip actual sending)
        service = EmailNotificationService(
            notification_repository=notif_repo,
            smtp_host=None,
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_use_tls=True,
            from_email="noreply@test.com",
            from_name="Test"
        )
        
        notification = Notification(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="email",
            title="Test Email",
            body="Test body",
            data={}
        )
        
        # Should return False when SMTP not configured
        success = await service.send_email_notification(
            to_email="test@example.com",
            notification=notification
        )
        
        assert success is False
    
    async def test_render_email_template(self, test_session: Session):
        """Test rendering email template"""
        notif_repo = NotificationLogRepository(test_session)
        
        service = EmailNotificationService(
            notification_repository=notif_repo,
            smtp_host=None,
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_use_tls=True,
            from_email="noreply@test.com",
            from_name="Test"
        )
        
        html = service.render_email_template(
            title="Test Email",
            body="This is a test",
            data={"days_since": 7}
        )
        
        assert "Test Email" in html
        assert "This is a test" in html


@pytest.mark.asyncio
class TestNotificationDispatchService:
    """Tests for NotificationDispatchService"""
    
    async def test_dispatch_notification_sends_push_when_enabled(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test dispatching notification sends push when enabled"""
        # Setup preferences
        sample_user_profile.notifications_enabled = True
        sample_user_profile.push_notifications_enabled = True
        sample_user_profile.email_notifications_enabled = False
        test_session.commit()
        
        # Create mock services
        preference_service = NotificationPreferenceService(test_session)
        
        device_repo = DeviceTokenRepository(test_session)
        notif_repo = NotificationLogRepository(test_session)
        
        # Register a device
        await device_repo.register_device(
            user_id=sample_user.id,
            device_token="test-token",
            platform="ios",
            device_info={}
        )
        
        push_service = PushNotificationService(
            device_repository=device_repo,
            notification_repository=notif_repo,
            fcm_credentials_path=None
        )
        
        email_service = EmailNotificationService(
            notification_repository=notif_repo,
            smtp_host=None,
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_use_tls=True,
            from_email="test@test.com",
            from_name="Test"
        )
        
        dispatch_service = NotificationDispatchService(
            preference_service=preference_service,
            push_service=push_service,
            email_service=email_service
        )
        
        notification = Notification(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="both",
            title="Test",
            body="Test",
            data={}
        )
        
        result = await dispatch_service.dispatch_notification(
            user_id=sample_user.id,
            notification=notification,
            email_address=None
        )
        
        # Should send push successfully
        assert result["push"]["sent"] is True
        assert result["push"]["count"] == 1
        
        # Should skip email (not configured)
        assert result["email"]["sent"] is False
    
    async def test_dispatch_notification_respects_preferences(
        self, test_session: Session, sample_user: User, sample_user_profile: UserProfile
    ):
        """Test dispatch respects user preferences"""
        # Disable all notifications
        sample_user_profile.notifications_enabled = False
        test_session.commit()
        
        preference_service = NotificationPreferenceService(test_session)
        device_repo = DeviceTokenRepository(test_session)
        notif_repo = NotificationLogRepository(test_session)
        
        push_service = PushNotificationService(
            device_repository=device_repo,
            notification_repository=notif_repo,
            fcm_credentials_path=None
        )
        
        email_service = EmailNotificationService(
            notification_repository=notif_repo,
            smtp_host=None,
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_use_tls=True,
            from_email="test@test.com",
            from_name="Test"
        )
        
        dispatch_service = NotificationDispatchService(
            preference_service=preference_service,
            push_service=push_service,
            email_service=email_service
        )
        
        notification = Notification(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="both",
            title="Test",
            body="Test",
            data={}
        )
        
        result = await dispatch_service.dispatch_notification(
            user_id=sample_user.id,
            notification=notification,
            email_address="test@example.com"
        )
        
        # Should not send anything when notifications disabled
        assert result["push"]["sent"] is False
        assert result["email"]["sent"] is False

