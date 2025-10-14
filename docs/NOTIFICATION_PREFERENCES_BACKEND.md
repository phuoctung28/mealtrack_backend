# Notification Preferences Backend Specification

## 1. Introduction

### 1.1 Purpose
This document specifies the backend requirements for the notification preferences system, enabling storage, management, and delivery of user notification preferences across the Nutree AI platform.

### 1.2 Scope
This specification covers:
- User notification preference storage and APIs
- Device token management for push notifications
- Push notification delivery via FCM/APNs
- Email notification delivery
- Notification scheduling and dispatch
- Notification history and analytics

### 1.3 Definitions and Acronyms
- **FCM**: Firebase Cloud Messaging
- **APNs**: Apple Push Notification service
- **DTO**: Data Transfer Object
- **TTL**: Time To Live
- **SMTP**: Simple Mail Transfer Protocol

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Mobile Clients                           │
│                     (iOS, Android, Web)                         │
└──────────────────────────┬──────────────────────────────────────┘
                          │
                          │ HTTPS / REST API
                          │
┌──────────────────────────▼──────────────────────────────────────┐
│                      API Gateway Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NotificationPreferencesController                       │  │
│  │  DeviceTokenController                                   │  │
│  │  NotificationTriggerController (Admin)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                          │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Service Layer                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NotificationPreferenceService                           │  │
│  │  PushNotificationService (FCM/APNs)                      │  │
│  │  EmailNotificationService (SMTP/SendGrid)                │  │
│  │  NotificationTemplateService                             │  │
│  │  NotificationDispatchService                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                          │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Repository Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  UserPreferenceRepository                                │  │
│  │  DeviceTokenRepository                                   │  │
│  │  NotificationLogRepository                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                          │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Database Layer                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  user_preferences (existing table, add columns)          │  │
│  │  device_tokens (new table)                               │  │
│  │  notification_logs (new table)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

External Services:
  - Firebase Cloud Messaging (FCM)
  - Apple Push Notification service (APNs)
  - Email Service (SendGrid / AWS SES)
```

## 3. Database Schema

### 3.1 User Preferences Table Update

Add notification preference columns to existing `user_preferences` table:

```sql
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS push_notifications_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS weekly_weight_reminder_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS weekly_weight_reminder_day INTEGER DEFAULT 0 CHECK (weekly_weight_reminder_day >= 0 AND weekly_weight_reminder_day <= 6);
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS weekly_weight_reminder_time VARCHAR(5) DEFAULT '09:00' CHECK (weekly_weight_reminder_time ~ '^\d{2}:\d{2}$');
```

**Field Descriptions**:
- `notifications_enabled`: Master toggle for all notifications
- `push_notifications_enabled`: Enable push notifications to devices
- `email_notifications_enabled`: Enable email notifications
- `weekly_weight_reminder_enabled`: Enable weekly weight update reminder
- `weekly_weight_reminder_day`: Day of week (0=Sunday, 6=Saturday)
- `weekly_weight_reminder_time`: Time in HH:mm format (24-hour)

### 3.2 Device Tokens Table (New)

```sql
CREATE TABLE device_tokens (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    device_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_device_token UNIQUE (device_token)
);

CREATE INDEX idx_device_tokens_user_id ON device_tokens(user_id);
CREATE INDEX idx_device_tokens_active ON device_tokens(user_id, is_active);
CREATE INDEX idx_device_tokens_last_used ON device_tokens(last_used_at);
```

**Field Descriptions**:
- `id`: Unique device registration ID
- `user_id`: Reference to user who owns the device
- `device_token`: FCM/APNs token for the device
- `platform`: Device platform (ios/android/web)
- `device_info`: JSON with device model, OS version, app version
- `is_active`: Whether token is still valid
- `last_used_at`: Last time device received notification
- `created_at`: When device was registered
- `updated_at`: Last update timestamp

### 3.3 Notification Logs Table (New)

```sql
CREATE TABLE notification_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    delivery_method VARCHAR(20) NOT NULL CHECK (delivery_method IN ('push', 'email')),
    title VARCHAR(255),
    body TEXT,
    data JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sent', 'delivered', 'failed', 'opened')),
    device_token_id VARCHAR(36) REFERENCES device_tokens(id) ON DELETE SET NULL,
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_notification_type CHECK (notification_type IN (
        'weight_reminder',
        'meal_reminder',
        'achievement',
        'goal_progress',
        'social',
        'system'
    ))
);

CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at);
CREATE INDEX idx_notification_logs_user_type ON notification_logs(user_id, notification_type);
```

**Field Descriptions**:
- `id`: Unique notification log ID
- `user_id`: User who received the notification
- `notification_type`: Type of notification (weight_reminder, etc.)
- `delivery_method`: How notification was sent (push/email)
- `title`: Notification title
- `body`: Notification body text
- `data`: Additional notification payload data
- `status`: Current delivery status
- `device_token_id`: Reference to device that received notification
- `error_message`: Error details if delivery failed
- `sent_at`: When notification was sent
- `delivered_at`: When notification was delivered
- `opened_at`: When user opened notification
- `created_at`: When log entry was created

### 3.4 Migration Script

```python
"""Add notification preferences support

Revision ID: 008_notification_preferences
Revises: 007_previous_migration
Create Date: 2025-10-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '008_notification_preferences'
down_revision = '007_previous_migration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add notification preference columns to user_preferences
    op.add_column('user_preferences', 
        sa.Column('notifications_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user_preferences', 
        sa.Column('push_notifications_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user_preferences', 
        sa.Column('email_notifications_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('user_preferences', 
        sa.Column('weekly_weight_reminder_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('user_preferences', 
        sa.Column('weekly_weight_reminder_day', sa.Integer(), server_default='0', nullable=False))
    op.add_column('user_preferences', 
        sa.Column('weekly_weight_reminder_time', sa.String(5), server_default='09:00', nullable=False))
    
    # Add constraints
    op.create_check_constraint(
        'check_reminder_day_range',
        'user_preferences',
        'weekly_weight_reminder_day >= 0 AND weekly_weight_reminder_day <= 6'
    )
    op.create_check_constraint(
        'check_reminder_time_format',
        'user_preferences',
        "weekly_weight_reminder_time ~ '^\\d{2}:\\d{2}$'"
    )
    
    # Create device_tokens table
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_token', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('device_info', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_check_constraint(
        'check_platform_valid',
        'device_tokens',
        "platform IN ('ios', 'android', 'web')"
    )
    op.create_unique_constraint('unique_device_token', 'device_tokens', ['device_token'])
    op.create_index('idx_device_tokens_user_id', 'device_tokens', ['user_id'])
    op.create_index('idx_device_tokens_active', 'device_tokens', ['user_id', 'is_active'])
    op.create_index('idx_device_tokens_last_used', 'device_tokens', ['last_used_at'])
    
    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('delivery_method', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('device_token_id', sa.String(36), sa.ForeignKey('device_tokens.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_check_constraint(
        'check_delivery_method_valid',
        'notification_logs',
        "delivery_method IN ('push', 'email')"
    )
    op.create_check_constraint(
        'check_status_valid',
        'notification_logs',
        "status IN ('pending', 'sent', 'delivered', 'failed', 'opened')"
    )
    op.create_check_constraint(
        'check_notification_type_valid',
        'notification_logs',
        "notification_type IN ('weight_reminder', 'meal_reminder', 'achievement', 'goal_progress', 'social', 'system')"
    )
    
    op.create_index('idx_notification_logs_user_id', 'notification_logs', ['user_id'])
    op.create_index('idx_notification_logs_type', 'notification_logs', ['notification_type'])
    op.create_index('idx_notification_logs_status', 'notification_logs', ['status'])
    op.create_index('idx_notification_logs_created_at', 'notification_logs', ['created_at'])
    op.create_index('idx_notification_logs_user_type', 'notification_logs', ['user_id', 'notification_type'])

def downgrade() -> None:
    # Drop tables
    op.drop_table('notification_logs')
    op.drop_table('device_tokens')
    
    # Remove columns from user_preferences
    op.drop_column('user_preferences', 'weekly_weight_reminder_time')
    op.drop_column('user_preferences', 'weekly_weight_reminder_day')
    op.drop_column('user_preferences', 'weekly_weight_reminder_enabled')
    op.drop_column('user_preferences', 'email_notifications_enabled')
    op.drop_column('user_preferences', 'push_notifications_enabled')
    op.drop_column('user_preferences', 'notifications_enabled')
```

## 4. API Endpoints

### 4.1 Update Notification Preferences

**Endpoint**: `PUT /api/v1/users/{user_id}/preferences/notifications`

**Authentication**: Required (user must own the resource)

**Request Body**:
```json
{
  "notifications_enabled": true,
  "push_notifications_enabled": true,
  "email_notifications_enabled": false,
  "weekly_weight_reminder_enabled": true,
  "weekly_weight_reminder_day": 0,
  "weekly_weight_reminder_time": "09:00"
}
```

**Response** (200 OK):
```json
{
  "user_id": "abc123",
  "preferences": {
    "notifications_enabled": true,
    "push_notifications_enabled": true,
    "email_notifications_enabled": false,
    "weekly_weight_reminder_enabled": true,
    "weekly_weight_reminder_day": 0,
    "weekly_weight_reminder_time": "09:00"
  },
  "updated_at": "2025-10-11T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid preference values
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: User cannot modify this resource
- `404 Not Found`: User not found

### 4.2 Get Notification Preferences

**Endpoint**: `GET /api/v1/users/{user_id}/preferences/notifications`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "user_id": "abc123",
  "preferences": {
    "notifications_enabled": true,
    "push_notifications_enabled": true,
    "email_notifications_enabled": false,
    "weekly_weight_reminder_enabled": true,
    "weekly_weight_reminder_day": 0,
    "weekly_weight_reminder_time": "09:00"
  }
}
```

### 4.3 Register Device Token

**Endpoint**: `POST /api/v1/users/{user_id}/devices`

**Authentication**: Required

**Request Body**:
```json
{
  "device_token": "fK7xY9dH3mN...",
  "platform": "ios",
  "device_info": {
    "model": "iPhone 14 Pro",
    "os_version": "17.0",
    "app_version": "1.2.0"
  }
}
```

**Response** (201 Created):
```json
{
  "device_id": "device123",
  "user_id": "abc123",
  "device_token": "fK7xY9dH3mN...",
  "platform": "ios",
  "is_active": true,
  "created_at": "2025-10-11T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid device token or platform
- `401 Unauthorized`: Missing or invalid authentication
- `409 Conflict`: Device token already registered

### 4.4 Unregister Device Token

**Endpoint**: `DELETE /api/v1/users/{user_id}/devices/{device_id}`

**Authentication**: Required

**Response** (204 No Content)

**Error Responses**:
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Device not found

### 4.5 List User Devices

**Endpoint**: `GET /api/v1/users/{user_id}/devices`

**Authentication**: Required

**Query Parameters**:
- `active_only`: boolean (default: true)

**Response** (200 OK):
```json
{
  "devices": [
    {
      "device_id": "device123",
      "platform": "ios",
      "device_info": {
        "model": "iPhone 14 Pro",
        "os_version": "17.0",
        "app_version": "1.2.0"
      },
      "is_active": true,
      "last_used_at": "2025-10-11T10:30:00Z",
      "created_at": "2025-10-01T08:00:00Z"
    }
  ],
  "total": 1
}
```

### 4.6 Send Test Notification

**Endpoint**: `POST /api/v1/users/{user_id}/notifications/test`

**Authentication**: Required

**Request Body**:
```json
{
  "notification_type": "weight_reminder",
  "delivery_method": "push"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "notification_id": "notif123",
  "message": "Test notification sent successfully"
}
```

### 4.7 Get Notification History

**Endpoint**: `GET /api/v1/users/{user_id}/notifications/history`

**Authentication**: Required

**Query Parameters**:
- `notification_type`: string (optional, filter by type)
- `limit`: integer (default: 50, max: 100)
- `offset`: integer (default: 0)
- `start_date`: ISO8601 date (optional)
- `end_date`: ISO8601 date (optional)

**Response** (200 OK):
```json
{
  "notifications": [
    {
      "id": "notif123",
      "notification_type": "weight_reminder",
      "delivery_method": "push",
      "title": "Time to update your weight! ⚖️",
      "body": "It's been 7 days since your last update.",
      "status": "delivered",
      "sent_at": "2025-10-11T09:00:00Z",
      "delivered_at": "2025-10-11T09:00:05Z",
      "opened_at": "2025-10-11T09:15:30Z"
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

### 4.8 Trigger Notification (Admin Only)

**Endpoint**: `POST /api/v1/admin/notifications/trigger`

**Authentication**: Required (Admin role)

**Request Body**:
```json
{
  "user_ids": ["user1", "user2"],
  "notification_type": "system",
  "title": "App Update Available",
  "body": "Version 2.0 is now available with new features!",
  "data": {
    "action": "update_app",
    "version": "2.0.0"
  }
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "job123",
  "message": "Notification dispatch initiated",
  "target_users": 2
}
```

## 5. Domain Models

### 5.1 NotificationPreferences

```python
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
        if not (0 <= self.weekly_weight_reminder_day <= 6):
            raise ValueError("Reminder day must be 0-6")
        if not self._is_valid_time(self.weekly_weight_reminder_time):
            raise ValueError("Reminder time must be in HH:mm format")
    
    @staticmethod
    def _is_valid_time(time_str: str) -> bool:
        """Validate time format HH:mm"""
        import re
        return bool(re.match(r'^\d{2}:\d{2}$', time_str))
    
    def can_send_push(self) -> bool:
        """Check if push notifications are allowed"""
        return self.notifications_enabled and self.push_notifications_enabled
    
    def can_send_email(self) -> bool:
        """Check if email notifications are allowed"""
        return self.notifications_enabled and self.email_notifications_enabled
```

### 5.2 DeviceToken

```python
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
        if self.platform not in ['ios', 'android', 'web']:
            raise ValueError("Platform must be ios, android, or web")
```

### 5.3 Notification

```python
@dataclass
class Notification:
    """Notification to be sent"""
    user_id: str
    notification_type: str
    delivery_method: str  # 'push' or 'email'
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.notification_type not in [
            'weight_reminder', 'meal_reminder', 'achievement',
            'goal_progress', 'social', 'system'
        ]:
            raise ValueError(f"Invalid notification type: {self.notification_type}")
        
        if self.delivery_method not in ['push', 'email']:
            raise ValueError("Delivery method must be push or email")
```

### 5.4 NotificationLog

```python
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
```

## 6. Service Implementation

### 6.1 NotificationPreferenceService

```python
class NotificationPreferenceService:
    """Service for managing notification preferences"""
    
    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
        event_publisher: EventPublisher
    ):
        self.preference_repository = preference_repository
        self.event_publisher = event_publisher
    
    async def update_preferences(
        self,
        user_id: str,
        preferences: NotificationPreferences
    ) -> NotificationPreferences:
        """Update user notification preferences"""
        # Validate preferences
        preferences.__post_init__()
        
        # Save to database
        updated = await self.preference_repository.update_notification_preferences(
            user_id, preferences
        )
        
        # Publish event for other services
        await self.event_publisher.publish(
            NotificationPreferencesUpdatedEvent(
                user_id=user_id,
                preferences=updated
            )
        )
        
        return updated
    
    async def get_preferences(
        self,
        user_id: str
    ) -> NotificationPreferences:
        """Get user notification preferences"""
        return await self.preference_repository.get_notification_preferences(user_id)
    
    async def can_send_notification(
        self,
        user_id: str,
        notification_type: str,
        delivery_method: str
    ) -> bool:
        """Check if notification can be sent to user"""
        preferences = await self.get_preferences(user_id)
        
        if not preferences.notifications_enabled:
            return False
        
        if delivery_method == 'push':
            return preferences.can_send_push()
        elif delivery_method == 'email':
            return preferences.can_send_email()
        
        return False
```

### 6.2 PushNotificationService

```python
class PushNotificationService:
    """Service for sending push notifications"""
    
    def __init__(
        self,
        fcm_client: FCMClient,
        apns_client: APNsClient,
        device_repository: DeviceTokenRepository,
        notification_repository: NotificationLogRepository
    ):
        self.fcm_client = fcm_client
        self.apns_client = apns_client
        self.device_repository = device_repository
        self.notification_repository = notification_repository
    
    async def send_push_notification(
        self,
        user_id: str,
        notification: Notification
    ) -> List[str]:
        """Send push notification to all user devices"""
        # Get active devices for user
        devices = await self.device_repository.get_active_devices(user_id)
        
        if not devices:
            logger.info(f"No active devices for user {user_id}")
            return []
        
        sent_notification_ids = []
        
        for device in devices:
            try:
                # Create notification log
                log_id = await self.notification_repository.create_log(
                    user_id=user_id,
                    notification=notification,
                    device_token_id=device.id
                )
                
                # Send to appropriate platform
                if device.platform == 'ios':
                    await self._send_to_apns(device, notification)
                elif device.platform == 'android':
                    await self._send_to_fcm(device, notification)
                
                # Update log status
                await self.notification_repository.update_status(
                    log_id, 'sent', sent_at=datetime.utcnow()
                )
                
                # Update device last used
                await self.device_repository.update_last_used(device.id)
                
                sent_notification_ids.append(log_id)
                
            except Exception as e:
                logger.error(f"Failed to send notification to device {device.id}: {e}")
                await self.notification_repository.update_status(
                    log_id, 'failed', error_message=str(e)
                )
                
                # Mark device as inactive if token is invalid
                if self._is_invalid_token_error(e):
                    await self.device_repository.mark_inactive(device.id)
        
        return sent_notification_ids
    
    async def _send_to_fcm(self, device: DeviceToken, notification: Notification):
        """Send notification via Firebase Cloud Messaging"""
        message = {
            'token': device.device_token,
            'notification': {
                'title': notification.title,
                'body': notification.body,
            },
            'data': notification.data,
            'android': {
                'priority': 'high',
                'notification': {
                    'sound': 'default',
                    'channel_id': self._get_channel_id(notification.notification_type)
                }
            }
        }
        
        await self.fcm_client.send(message)
    
    async def _send_to_apns(self, device: DeviceToken, notification: Notification):
        """Send notification via Apple Push Notification service"""
        payload = {
            'aps': {
                'alert': {
                    'title': notification.title,
                    'body': notification.body
                },
                'sound': 'default',
                'badge': 1,
                'category': self._get_category_id(notification.notification_type)
            },
            'data': notification.data
        }
        
        await self.apns_client.send(device.device_token, payload)
    
    @staticmethod
    def _get_channel_id(notification_type: str) -> str:
        """Get Android notification channel ID for type"""
        channel_map = {
            'weight_reminder': 'reminders',
            'meal_reminder': 'reminders',
            'achievement': 'achievements',
            'goal_progress': 'progress',
            'social': 'social',
            'system': 'system'
        }
        return channel_map.get(notification_type, 'default')
    
    @staticmethod
    def _get_category_id(notification_type: str) -> str:
        """Get iOS notification category ID for type"""
        return notification_type.upper()
    
    @staticmethod
    def _is_invalid_token_error(error: Exception) -> bool:
        """Check if error indicates invalid device token"""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            'invalid', 'unregistered', 'notfound', 'mismatchsenderid'
        ])
```

### 6.3 EmailNotificationService

```python
class EmailNotificationService:
    """Service for sending email notifications"""
    
    def __init__(
        self,
        email_client: EmailClient,
        user_repository: UserRepository,
        notification_repository: NotificationLogRepository,
        template_service: NotificationTemplateService
    ):
        self.email_client = email_client
        self.user_repository = user_repository
        self.notification_repository = notification_repository
        self.template_service = template_service
    
    async def send_email_notification(
        self,
        user_id: str,
        notification: Notification
    ) -> str:
        """Send email notification to user"""
        # Get user email
        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.email:
            raise ValueError(f"User {user_id} has no email address")
        
        if not user.email_verified:
            raise ValueError(f"User {user_id} email not verified")
        
        # Create notification log
        log_id = await self.notification_repository.create_log(
            user_id=user_id,
            notification=notification,
            device_token_id=None
        )
        
        try:
            # Generate email HTML from template
            html_content = await self.template_service.render_email_template(
                notification.notification_type,
                {
                    'user_name': user.display_name or user.email,
                    'title': notification.title,
                    'body': notification.body,
                    'data': notification.data
                }
            )
            
            # Send email
            await self.email_client.send(
                to=user.email,
                subject=notification.title,
                html=html_content
            )
            
            # Update log status
            await self.notification_repository.update_status(
                log_id, 'sent', sent_at=datetime.utcnow()
            )
            
            return log_id
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {e}")
            await self.notification_repository.update_status(
                log_id, 'failed', error_message=str(e)
            )
            raise
```

### 6.4 NotificationDispatchService

```python
class NotificationDispatchService:
    """Orchestrates notification sending across channels"""
    
    def __init__(
        self,
        preference_service: NotificationPreferenceService,
        push_service: PushNotificationService,
        email_service: EmailNotificationService
    ):
        self.preference_service = preference_service
        self.push_service = push_service
        self.email_service = email_service
    
    async def dispatch_notification(
        self,
        user_id: str,
        notification: Notification
    ) -> Dict[str, List[str]]:
        """Dispatch notification to all enabled channels"""
        results = {
            'push': [],
            'email': []
        }
        
        # Check if notifications are enabled
        preferences = await self.preference_service.get_preferences(user_id)
        
        if not preferences.notifications_enabled:
            logger.info(f"Notifications disabled for user {user_id}")
            return results
        
        # Send push notification if enabled
        if notification.delivery_method == 'push' and preferences.can_send_push():
            try:
                notification_ids = await self.push_service.send_push_notification(
                    user_id, notification
                )
                results['push'] = notification_ids
            except Exception as e:
                logger.error(f"Push notification failed for user {user_id}: {e}")
        
        # Send email notification if enabled
        if notification.delivery_method == 'email' and preferences.can_send_email():
            try:
                notification_id = await self.email_service.send_email_notification(
                    user_id, notification
                )
                results['email'] = [notification_id]
            except Exception as e:
                logger.error(f"Email notification failed for user {user_id}: {e}")
        
        return results
    
    async def dispatch_to_multiple_users(
        self,
        user_ids: List[str],
        notification_template: Notification
    ) -> Dict[str, Any]:
        """Dispatch notification to multiple users"""
        total_users = len(user_ids)
        successful = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                await self.dispatch_notification(user_id, notification_template)
                successful += 1
            except Exception as e:
                logger.error(f"Failed to dispatch to user {user_id}: {e}")
                failed += 1
        
        return {
            'total': total_users,
            'successful': successful,
            'failed': failed
        }
```

## 7. Background Jobs

### 7.1 Weekly Weight Reminder Job

```python
class WeeklyWeightReminderJob:
    """Background job to send weekly weight reminders"""
    
    def __init__(
        self,
        preference_service: NotificationPreferenceService,
        dispatch_service: NotificationDispatchService,
        user_repository: UserRepository,
        weight_repository: WeightHistoryRepository
    ):
        self.preference_service = preference_service
        self.dispatch_service = dispatch_service
        self.user_repository = user_repository
        self.weight_repository = weight_repository
    
    async def run(self):
        """Execute the reminder job"""
        logger.info("Starting weekly weight reminder job")
        
        # Get current day and time
        now = datetime.now()
        current_day = now.weekday()  # 0=Monday, 6=Sunday in Python
        # Convert to 0=Sunday, 6=Saturday to match our schema
        current_day = (current_day + 1) % 7
        current_time = now.strftime("%H:%M")
        
        # Find users with reminders scheduled for current day/time
        users = await self._find_users_to_remind(current_day, current_time)
        
        logger.info(f"Found {len(users)} users to remind")
        
        for user in users:
            try:
                # Get days since last weight update
                last_weight = await self.weight_repository.get_latest_for_user(user.id)
                days_since = self._calculate_days_since(last_weight)
                
                # Create notification
                notification = Notification(
                    user_id=user.id,
                    notification_type='weight_reminder',
                    delivery_method='push',
                    title="Time to update your weight! ⚖️",
                    body=f"It's been {days_since} days since your last update. Track your progress to stay on target.",
                    data={
                        'action': 'weight_update',
                        'days_since': days_since
                    }
                )
                
                # Dispatch notification
                await self.dispatch_service.dispatch_notification(user.id, notification)
                
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user.id}: {e}")
        
        logger.info("Weekly weight reminder job completed")
    
    async def _find_users_to_remind(
        self,
        day: int,
        time: str
    ) -> List[User]:
        """Find users who should receive reminder at this day/time"""
        # Query users with matching reminder schedule
        # Allow 5-minute window for execution
        return await self.user_repository.find_with_reminder_schedule(
            day=day,
            time_start=self._subtract_minutes(time, 5),
            time_end=self._add_minutes(time, 5)
        )
    
    @staticmethod
    def _calculate_days_since(last_weight: Optional[WeightEntry]) -> int:
        """Calculate days since last weight update"""
        if not last_weight:
            return 0
        
        return (datetime.now() - last_weight.recorded_at).days
    
    @staticmethod
    def _subtract_minutes(time_str: str, minutes: int) -> str:
        """Subtract minutes from HH:mm time string"""
        from datetime import datetime, timedelta
        time_obj = datetime.strptime(time_str, "%H:%M")
        new_time = time_obj - timedelta(minutes=minutes)
        return new_time.strftime("%H:%M")
    
    @staticmethod
    def _add_minutes(time_str: str, minutes: int) -> str:
        """Add minutes to HH:mm time string"""
        from datetime import datetime, timedelta
        time_obj = datetime.strptime(time_str, "%H:%M")
        new_time = time_obj + timedelta(minutes=minutes)
        return new_time.strftime("%H:%M")
```

### 7.2 Scheduler Configuration

```python
# In app startup or scheduler configuration

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Create scheduler
scheduler = AsyncIOScheduler()

# Schedule weekly weight reminder job to run every 5 minutes
# (to catch all time windows)
scheduler.add_job(
    weekly_weight_reminder_job.run,
    CronTrigger(minute='*/5'),
    id='weekly_weight_reminder',
    name='Send weekly weight reminders',
    replace_existing=True
)

# Start scheduler
scheduler.start()
```

## 8. Configuration and Environment Variables

### 8.1 Firebase Cloud Messaging (FCM)

```env
# Firebase configuration
FCM_PROJECT_ID=your-project-id
FCM_PRIVATE_KEY_ID=your-private-key-id
FCM_PRIVATE_KEY=your-private-key
FCM_CLIENT_EMAIL=your-client-email
FCM_CLIENT_ID=your-client-id
```

### 8.2 Apple Push Notification Service (APNs)

```env
# APNs configuration
APNS_KEY_ID=your-key-id
APNS_TEAM_ID=your-team-id
APNS_BUNDLE_ID=com.nutree.ai
APNS_PRIVATE_KEY_PATH=/path/to/AuthKey.p8
APNS_ENVIRONMENT=production  # or 'sandbox' for development
```

### 8.3 Email Service

```env
# Email configuration (SendGrid example)
EMAIL_API_KEY=your-sendgrid-api-key
EMAIL_FROM_ADDRESS=noreply@nutreeai.com
EMAIL_FROM_NAME=Nutree AI
EMAIL_REPLY_TO=support@nutreeai.com

# Or SMTP configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

### 8.4 Notification Settings

```env
# Notification configuration
NOTIFICATION_MAX_RETRIES=3
NOTIFICATION_RETRY_DELAY_SECONDS=60
NOTIFICATION_BATCH_SIZE=100
NOTIFICATION_LOG_RETENTION_DAYS=30
DEVICE_TOKEN_INACTIVITY_DAYS=90
```

## 9. Testing Strategy

### 9.1 Unit Tests

Test individual components:
- NotificationPreferences validation
- NotificationDispatchService logic
- Permission checking logic
- Time calculation functions

### 9.2 Integration Tests

Test service integration:
- Preference update and retrieval
- Device token registration/unregistration
- Notification log creation and updates
- Background job execution

### 9.3 End-to-End Tests

Test complete flows:
- User updates preferences → API → Database
- Push notification dispatch → FCM/APNs → Device
- Email notification dispatch → Email service → Inbox
- Weekly reminder job → Notification delivery

### 9.4 Mock External Services

Mock external services for testing:
- Mock FCM client
- Mock APNs client
- Mock email client
- Mock time/date functions

## 10. Monitoring and Observability

### 10.1 Metrics to Track

- Notification dispatch rate (per type)
- Notification delivery success rate
- Notification open rate
- Email bounce rate
- Device token registration rate
- Device token invalidation rate
- API endpoint response times
- Background job execution time

### 10.2 Alerts

Configure alerts for:
- Notification delivery rate drops below 90%
- Email bounce rate exceeds 5%
- API error rate exceeds 1%
- Background job failures
- Database connection issues

### 10.3 Logging

Log important events:
- Preference updates
- Device registrations/unregistrations
- Notification dispatches
- Delivery failures
- Invalid device tokens
- Background job execution

## 11. Security Considerations

### 11.1 Authentication and Authorization

- All endpoints require valid JWT authentication
- Users can only modify their own preferences
- Device token endpoints require device ownership validation
- Admin endpoints require admin role

### 11.2 Data Protection

- Device tokens encrypted at rest
- HTTPS required for all API communications
- Email addresses masked in logs
- Notification content sanitized

### 11.3 Rate Limiting

- API endpoints rate-limited per user
- Notification dispatch rate-limited to prevent spam
- Device registration rate-limited to prevent abuse

## 12. Deployment Checklist

### Phase 1: Database and Core APIs
- [ ] Run database migration
- [ ] Deploy preference update API
- [ ] Deploy device registration API
- [ ] Test preference sync
- [ ] Test device registration

### Phase 2: Push Notifications
- [ ] Configure FCM credentials
- [ ] Configure APNs credentials
- [ ] Deploy push notification service
- [ ] Test push delivery to iOS
- [ ] Test push delivery to Android

### Phase 3: Email Notifications
- [ ] Configure email service credentials
- [ ] Create email templates
- [ ] Deploy email notification service
- [ ] Test email delivery
- [ ] Test unsubscribe flow

### Phase 4: Background Jobs
- [ ] Deploy weekly reminder job
- [ ] Configure job scheduler
- [ ] Test job execution
- [ ] Monitor job performance

### Phase 5: Monitoring
- [ ] Set up metrics collection
- [ ] Configure alerts
- [ ] Set up log aggregation
- [ ] Create monitoring dashboard

## 13. Future Enhancements

1. **Notification Scheduling Optimization**: Machine learning to find optimal notification times per user
2. **Rich Notifications**: Support for images, action buttons, inline replies
3. **Notification Templates**: Admin interface to manage notification templates
4. **A/B Testing**: Framework for testing notification content effectiveness
5. **Personalization**: Dynamic notification content based on user behavior
6. **Notification Campaigns**: Bulk notification sending with targeting
7. **Real-time Notifications**: WebSocket-based real-time updates
8. **Notification Preferences API V2**: More granular per-type preferences
9. **Multi-language Support**: Localized notification content
10. **Notification Analytics Dashboard**: Comprehensive analytics UI

---

This backend specification provides a complete foundation for implementing the notification preferences system with push notifications, email notifications, and scheduled reminders.

