"""
Domain models for notification system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import re


# Constants
TIME_FORMAT_PATTERN = r'^[0-2][0-9]:[0-5][0-9]$'  # HH:mm format (e.g., 09:00, 23:59)


@dataclass
class NotificationPreferences:
    """User notification preferences"""
    notifications_enabled: bool
    push_notifications_enabled: bool
    email_notifications_enabled: bool
    weekly_weight_reminder_enabled: bool
    weekly_weight_reminder_day: int  # 0-6 (Sunday-Saturday)
    weekly_weight_reminder_time: str  # HH:mm format
    
    def __post_init__(self):
        """Validate preferences on initialization"""
        if not (0 <= self.weekly_weight_reminder_day <= 6):
            raise ValueError("Reminder day must be 0-6 (0=Sunday, 6=Saturday)")
        if not self._is_valid_time(self.weekly_weight_reminder_time):
            raise ValueError("Reminder time must be in HH:mm format (e.g., 09:00)")
    
    @staticmethod
    def _is_valid_time(time_str: str) -> bool:
        """Validate time format HH:mm (00:00 to 23:59)"""
        if not re.match(TIME_FORMAT_PATTERN, time_str):
            return False
        # Additional validation for hours 00-23
        hours = int(time_str.split(':')[0])
        return 0 <= hours <= 23
    
    def can_send_push(self) -> bool:
        """Check if push notifications are allowed"""
        return self.notifications_enabled and self.push_notifications_enabled
    
    def can_send_email(self) -> bool:
        """Check if email notifications are allowed"""
        return self.notifications_enabled and self.email_notifications_enabled
    
    @classmethod
    def create_default(cls) -> 'NotificationPreferences':
        """Create default notification preferences"""
        return cls(
            notifications_enabled=True,
            push_notifications_enabled=True,
            email_notifications_enabled=False,
            weekly_weight_reminder_enabled=False,
            weekly_weight_reminder_day=0,  # Sunday
            weekly_weight_reminder_time='09:00'
        )


@dataclass
class DeviceToken:
    """Device token for push notifications"""
    id: str
    user_id: str
    device_token: str
    platform: str  # 'ios', 'android', 'web'
    device_info: Dict[str, Any]
    is_active: bool
    last_used_at: datetime
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate device token on initialization"""
        if self.platform not in ['ios', 'android', 'web']:
            raise ValueError("Platform must be one of: ios, android, web")
        
        if not self.device_token:
            raise ValueError("Device token cannot be empty")


@dataclass
class Notification:
    """Notification to be sent"""
    user_id: str
    notification_type: str
    delivery_method: str  # 'push' or 'email'
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Valid notification types
    VALID_TYPES = [
        'weight_reminder',
        'meal_reminder',
        'achievement',
        'goal_progress',
        'social',
        'system'
    ]
    
    def __post_init__(self):
        """Validate notification on initialization"""
        if self.notification_type not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid notification type: {self.notification_type}. "
                f"Must be one of: {', '.join(self.VALID_TYPES)}"
            )
        
        if self.delivery_method not in ['push', 'email']:
            raise ValueError("Delivery method must be 'push' or 'email'")
        
        if not self.title:
            raise ValueError("Notification title cannot be empty")
        
        if not self.body:
            raise ValueError("Notification body cannot be empty")


@dataclass
class NotificationLog:
    """Log of sent notification"""
    id: str
    user_id: str
    notification_type: str
    delivery_method: str
    title: str
    body: str
    data: Dict[str, Any]
    status: str  # 'pending', 'sent', 'delivered', 'failed', 'opened'
    device_token_id: Optional[str]
    error_message: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    created_at: datetime
    
    # Valid statuses
    VALID_STATUSES = ['pending', 'sent', 'delivered', 'failed', 'opened']
    
    def __post_init__(self):
        """Validate notification log on initialization"""
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {self.status}. "
                f"Must be one of: {', '.join(self.VALID_STATUSES)}"
            )
    
    def mark_sent(self, timestamp: datetime):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timestamp
    
    def mark_delivered(self, timestamp: datetime):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timestamp
    
    def mark_failed(self, error_message: str):
        """Mark notification as failed"""
        self.status = 'failed'
        self.error_message = error_message
    
    def mark_opened(self, timestamp: datetime):
        """Mark notification as opened"""
        self.status = 'opened'
        self.opened_at = timestamp


@dataclass
class NotificationTemplate:
    """Template for generating notification content"""
    notification_type: str
    title_template: str
    body_template: str
    
    def render(self, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render template with context data
        
        Returns:
            tuple: (rendered_title, rendered_body)
        """
        title = self.title_template.format(**context)
        body = self.body_template.format(**context)
        return title, body


# Predefined notification templates
NOTIFICATION_TEMPLATES = {
    'weight_reminder': NotificationTemplate(
        notification_type='weight_reminder',
        title_template="Time to update your weight! ⚖️",
        body_template="It's been {days_since} days since your last update. Track your progress to stay on target."
    ),
    'meal_reminder': NotificationTemplate(
        notification_type='meal_reminder',
        title_template="Time for {meal_type}! 🍽️",
        body_template="Remember to log your meal to stay on track with your goals."
    ),
    'achievement': NotificationTemplate(
        notification_type='achievement',
        title_template="Congratulations! 🎉",
        body_template="{achievement_text}"
    ),
    'goal_progress': NotificationTemplate(
        notification_type='goal_progress',
        title_template="You're {progress_percent}% to your goal!",
        body_template="Keep up the great work!"
    ),
    'system': NotificationTemplate(
        notification_type='system',
        title_template="{title}",
        body_template="{message}"
    )
}


def get_notification_template(notification_type: str) -> Optional[NotificationTemplate]:
    """Get notification template by type"""
    return NOTIFICATION_TEMPLATES.get(notification_type)

