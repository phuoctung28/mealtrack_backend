"""
Unit tests for notification domain models.
"""
import pytest
from datetime import datetime

from src.domain.model.notification import (
    NotificationPreferences,
    DeviceToken,
    Notification,
    NotificationLog,
    get_notification_template
)


class TestNotificationPreferences:
    """Tests for NotificationPreferences domain model"""
    
    def test_create_valid_preferences(self):
        """Test creating valid notification preferences"""
        prefs = NotificationPreferences(
            notifications_enabled=True,
            push_notifications_enabled=True,
            email_notifications_enabled=False,
            weekly_weight_reminder_enabled=True,
            weekly_weight_reminder_day=0,  # Sunday
            weekly_weight_reminder_time="09:00"
        )
        
        assert prefs.notifications_enabled is True
        assert prefs.push_notifications_enabled is True
        assert prefs.weekly_weight_reminder_day == 0
        assert prefs.weekly_weight_reminder_time == "09:00"
    
    def test_create_default_preferences(self):
        """Test creating default notification preferences"""
        prefs = NotificationPreferences.create_default()
        
        assert prefs.notifications_enabled is True
        assert prefs.push_notifications_enabled is True
        assert prefs.email_notifications_enabled is False
        assert prefs.weekly_weight_reminder_enabled is False
        assert prefs.weekly_weight_reminder_day == 0
        assert prefs.weekly_weight_reminder_time == "09:00"
    
    def test_invalid_reminder_day_raises_error(self):
        """Test that invalid reminder day raises ValueError"""
        with pytest.raises(ValueError, match="Reminder day must be 0-6"):
            NotificationPreferences(
                notifications_enabled=True,
                push_notifications_enabled=True,
                email_notifications_enabled=False,
                weekly_weight_reminder_enabled=True,
                weekly_weight_reminder_day=7,  # Invalid!
                weekly_weight_reminder_time="09:00"
            )
    
    def test_invalid_reminder_time_raises_error(self):
        """Test that invalid reminder time raises ValueError"""
        with pytest.raises(ValueError, match="Reminder time must be in HH:mm format"):
            NotificationPreferences(
                notifications_enabled=True,
                push_notifications_enabled=True,
                email_notifications_enabled=False,
                weekly_weight_reminder_enabled=True,
                weekly_weight_reminder_day=0,
                weekly_weight_reminder_time="25:00"  # Invalid hour!
            )
    
    def test_can_send_push_when_enabled(self):
        """Test can_send_push returns True when both flags enabled"""
        prefs = NotificationPreferences(
            notifications_enabled=True,
            push_notifications_enabled=True,
            email_notifications_enabled=False,
            weekly_weight_reminder_enabled=False,
            weekly_weight_reminder_day=0,
            weekly_weight_reminder_time="09:00"
        )
        
        assert prefs.can_send_push() is True
    
    def test_can_send_push_when_disabled(self):
        """Test can_send_push returns False when notifications disabled"""
        prefs = NotificationPreferences(
            notifications_enabled=False,
            push_notifications_enabled=True,
            email_notifications_enabled=False,
            weekly_weight_reminder_enabled=False,
            weekly_weight_reminder_day=0,
            weekly_weight_reminder_time="09:00"
        )
        
        assert prefs.can_send_push() is False
    
    def test_can_send_email_when_enabled(self):
        """Test can_send_email returns True when both flags enabled"""
        prefs = NotificationPreferences(
            notifications_enabled=True,
            push_notifications_enabled=False,
            email_notifications_enabled=True,
            weekly_weight_reminder_enabled=False,
            weekly_weight_reminder_day=0,
            weekly_weight_reminder_time="09:00"
        )
        
        assert prefs.can_send_email() is True


class TestDeviceToken:
    """Tests for DeviceToken domain model"""
    
    def test_create_valid_device_token(self):
        """Test creating valid device token"""
        token = DeviceToken(
            id="device-123",
            user_id="user-456",
            device_token="fcm-token-xyz",
            platform="ios",
            device_info={"model": "iPhone 14", "os": "iOS 17"},
            is_active=True,
            last_used_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert token.id == "device-123"
        assert token.platform == "ios"
        assert token.is_active is True
    
    def test_invalid_platform_raises_error(self):
        """Test that invalid platform raises ValueError"""
        with pytest.raises(ValueError, match="Platform must be one of: ios, android, web"):
            DeviceToken(
                id="device-123",
                user_id="user-456",
                device_token="fcm-token-xyz",
                platform="invalid",  # Invalid!
                device_info={},
                is_active=True,
                last_used_at=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
    
    def test_empty_device_token_raises_error(self):
        """Test that empty device token raises ValueError"""
        with pytest.raises(ValueError, match="Device token cannot be empty"):
            DeviceToken(
                id="device-123",
                user_id="user-456",
                device_token="",  # Empty!
                platform="ios",
                device_info={},
                is_active=True,
                last_used_at=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


class TestNotification:
    """Tests for Notification domain model"""
    
    def test_create_valid_notification(self):
        """Test creating valid notification"""
        notification = Notification(
            user_id="user-123",
            notification_type="weight_reminder",
            delivery_method="push",
            title="Time to update your weight!",
            body="Track your progress",
            data={"days_since": 7}
        )
        
        assert notification.user_id == "user-123"
        assert notification.notification_type == "weight_reminder"
        assert notification.delivery_method == "push"
        assert notification.data["days_since"] == 7
    
    def test_invalid_notification_type_raises_error(self):
        """Test that invalid notification type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid notification type"):
            Notification(
                user_id="user-123",
                notification_type="invalid_type",
                delivery_method="push",
                title="Test",
                body="Test"
            )
    
    def test_invalid_delivery_method_raises_error(self):
        """Test that invalid delivery method raises ValueError"""
        with pytest.raises(ValueError, match="Delivery method must be"):
            Notification(
                user_id="user-123",
                notification_type="weight_reminder",
                delivery_method="sms",  # Invalid!
                title="Test",
                body="Test"
            )
    
    def test_empty_title_raises_error(self):
        """Test that empty title raises ValueError"""
        with pytest.raises(ValueError, match="Notification title cannot be empty"):
            Notification(
                user_id="user-123",
                notification_type="weight_reminder",
                delivery_method="push",
                title="",  # Empty!
                body="Test"
            )


class TestNotificationLog:
    """Tests for NotificationLog domain model"""
    
    def test_mark_sent(self):
        """Test marking notification as sent"""
        log = NotificationLog(
            id="log-123",
            user_id="user-456",
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test",
            body="Test",
            data={},
            status="pending",
            device_token_id="device-789",
            error_message=None,
            sent_at=None,
            delivered_at=None,
            opened_at=None,
            created_at=datetime.now()
        )
        
        sent_time = datetime.now()
        log.mark_sent(sent_time)
        
        assert log.status == "sent"
        assert log.sent_at == sent_time
    
    def test_mark_failed(self):
        """Test marking notification as failed"""
        log = NotificationLog(
            id="log-123",
            user_id="user-456",
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test",
            body="Test",
            data={},
            status="pending",
            device_token_id="device-789",
            error_message=None,
            sent_at=None,
            delivered_at=None,
            opened_at=None,
            created_at=datetime.now()
        )
        
        log.mark_failed("Invalid device token")
        
        assert log.status == "failed"
        assert log.error_message == "Invalid device token"


class TestNotificationTemplates:
    """Tests for notification templates"""
    
    def test_get_weight_reminder_template(self):
        """Test getting weight reminder template"""
        template = get_notification_template("weight_reminder")
        
        assert template is not None
        assert template.notification_type == "weight_reminder"
        assert "weight" in template.title_template.lower()
    
    def test_render_weight_reminder_template(self):
        """Test rendering weight reminder template"""
        template = get_notification_template("weight_reminder")
        
        title, body = template.render({"days_since": 7})
        
        assert "weight" in title.lower()
        assert "7" in body
    
    def test_get_invalid_template_returns_none(self):
        """Test getting invalid template returns None"""
        template = get_notification_template("invalid_type")
        
        assert template is None

