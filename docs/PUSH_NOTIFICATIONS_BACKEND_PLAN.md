# Push Notifications Backend Implementation Plan (Simplified)

## Overview

Simple backend implementation for push notifications using Firebase Cloud Messaging (FCM). Focus on essential functionality only.

## What Mobile Already Has

- FCM service with token management
- 12 notification types (meal reminders, water, sleep, progress, etc.)
- NotificationPreferences matching the JSON structure below
- Testing UI to preview notifications

## Database Schema

### Users Table (Timezone Column)

The `users` table includes a `timezone` column (added in migration 010):
- Column: `timezone VARCHAR(50) NOT NULL DEFAULT 'UTC'`
- Index: `idx_users_timezone` on `timezone` column
- Format: IANA timezone identifiers (e.g., "America/Los_Angeles", "Asia/Ho_Chi_Minh")
- Purpose: Enables timezone-aware notification scheduling

### 1. User FCM Tokens

```sql
CREATE TABLE user_fcm_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token VARCHAR(255) NOT NULL UNIQUE,
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('ios', 'android')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_user_fcm_tokens_user_id ON user_fcm_tokens(user_id);
CREATE INDEX idx_user_fcm_tokens_active ON user_fcm_tokens(is_active) WHERE is_active = TRUE;
```

### 2. Notification Preferences

```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    -- Notification Type Toggles
    meal_reminders_enabled BOOLEAN DEFAULT TRUE,
    water_reminders_enabled BOOLEAN DEFAULT TRUE,
    sleep_reminders_enabled BOOLEAN DEFAULT TRUE,
    progress_notifications_enabled BOOLEAN DEFAULT TRUE,
    reengagement_notifications_enabled BOOLEAN DEFAULT TRUE,

    -- Meal Reminder Timing (minutes from midnight: 0-1439)
    breakfast_time_minutes INTEGER CHECK (breakfast_time_minutes >= 0 AND breakfast_time_minutes < 1440),
    lunch_time_minutes INTEGER CHECK (lunch_time_minutes >= 0 AND lunch_time_minutes < 1440),
    dinner_time_minutes INTEGER CHECK (dinner_time_minutes >= 0 AND dinner_time_minutes < 1440),

    -- Water Reminder Settings
    water_reminder_interval_hours INTEGER DEFAULT 2 CHECK (water_reminder_interval_hours > 0),
    last_water_reminder_at TIMESTAMP WITH TIME ZONE,

    -- Sleep Reminder Timing (minutes from midnight)
    sleep_reminder_time_minutes INTEGER CHECK (sleep_reminder_time_minutes >= 0 AND sleep_reminder_time_minutes < 1440),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_preferences_user_id ON notification_preferences(user_id);
```

**Note:** Time is stored as minutes from midnight (e.g., 480 = 8:00 AM, 720 = 12:00 PM, 1080 = 6:00 PM)

## API Endpoints

### 1. Register FCM Token

**POST** `/api/v1/notifications/tokens`

**Request:**
```json
{
  "fcm_token": "string",
  "device_type": "ios" | "android"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Token registered"
}
```

### 2. Delete FCM Token (Logout)

**DELETE** `/api/v1/notifications/tokens`

**Request:**
```json
{
  "fcm_token": "string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Token deleted"
}
```

### 3. Get Notification Preferences

**GET** `/api/v1/notifications/preferences`

**Response:**
```json
{
  "meal_reminders_enabled": true,
  "water_reminders_enabled": true,
  "sleep_reminders_enabled": true,
  "progress_notifications_enabled": true,
  "reengagement_notifications_enabled": true,
  "breakfast_time_minutes": 480,
  "lunch_time_minutes": 720,
  "dinner_time_minutes": 1080,
  "water_reminder_interval_hours": 2,
  "sleep_reminder_time_minutes": 1320
}
```

### 4. Update Notification Preferences

**PUT** `/api/v1/notifications/preferences`

**Request:** (send only fields to update)
```json
{
  "meal_reminders_enabled": false,
  "breakfast_time_minutes": 420
}
```

**Response:**
```json
{
  "success": true,
  "preferences": { /* full preferences object */ }
}
```

## Notification Sending (Core Logic)

### Firebase Admin SDK Setup

```python
import firebase_admin
from firebase_admin import credentials, messaging

# Initialize once at startup
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

def send_notification(user_id: UUID, title: str, body: str, notification_type: str, data: dict = None):
    """Send push notification to user"""

    # 1. Get user's active tokens
    tokens = db.query("SELECT fcm_token FROM user_fcm_tokens WHERE user_id = ? AND is_active = true", user_id)

    if not tokens:
        return {"success": False, "reason": "no_tokens"}

    # 2. Check if notification type is enabled
    prefs = db.query("SELECT * FROM notification_preferences WHERE user_id = ?", user_id)

    # Example: Check if meal reminders are enabled
    if "meal_reminder" in notification_type and not prefs.meal_reminders_enabled:
        return {"success": False, "reason": "disabled"}

    # 3. Build and send FCM message
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=[t.fcm_token for t in tokens],
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='high_priority_channel',  # Match mobile channels
                sound='default'
            )
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=1)
            )
        )
    )

    response = messaging.send_multicast(message)

    # 4. Clean up invalid tokens
    if response.failure_count > 0:
        for idx, result in enumerate(response.responses):
            if not result.success:
                db.execute("UPDATE user_fcm_tokens SET is_active = false WHERE fcm_token = ?", tokens[idx])

    return {"success": True, "sent": response.success_count}
```

## Notification Scheduling (Background Jobs)

### Scheduled Jobs Setup

Use Celery (Python), Bull (Node.js), or cron jobs:

**1. Meal Reminders** (runs every minute)
```python
def check_meal_reminders():
    """Check if any users need meal reminders at current time"""

    current_minutes = (datetime.now().hour * 60) + datetime.now().minute

    # Find users with breakfast reminder at this time
    users = db.query("""
        SELECT user_id FROM notification_preferences
        WHERE meal_reminders_enabled = true
        AND breakfast_time_minutes = ?
    """, current_minutes)

    for user in users:
        send_notification(
            user_id=user.user_id,
            title="🍳 Breakfast Time!",
            body="Start your day right - log your breakfast",
            notification_type="meal_reminder_breakfast",
            data={"type": "meal_reminder_breakfast"}
        )
```

**2. Water Reminders** (runs every 15 minutes)
```python
def check_water_reminders():
    """Send water reminders based on user intervals"""

    # This is simplified - you need to track last water reminder sent time
    users = db.query("""
        SELECT user_id, water_reminder_interval_hours
        FROM notification_preferences
        WHERE water_reminders_enabled = true
    """)

    for user in users:
        # Check if enough time has passed since last reminder
        # (implement your own tracking logic)
        send_notification(
            user_id=user.user_id,
            title="💧 Hydration Check",
            body="Time to drink some water!",
            notification_type="water_reminder",
            data={"type": "water_reminder"}
        )
```

**3. Sleep Reminders** (runs every minute)
```python
def check_sleep_reminders():
    """Check if any users need sleep reminders"""

    current_minutes = (datetime.now().hour * 60) + datetime.now().minute

    users = db.query("""
        SELECT user_id FROM notification_preferences
        WHERE sleep_reminders_enabled = true
        AND sleep_reminder_time_minutes = ?
    """, current_minutes)

    for user in users:
        send_notification(
            user_id=user.user_id,
            title="😴 Sleep Time",
            body="Get ready for a good night's rest",
            notification_type="sleep_reminder",
            data={"type": "sleep_reminder"}
        )
```

## Implementation Steps

### Week 1: Core Setup
1. Create database tables and migrations
2. Implement FCM token POST/DELETE endpoints
3. Set up Firebase Admin SDK
4. Test token registration from mobile app

### Week 2: Preferences
1. Implement preferences GET/PUT endpoints
2. Create default preferences on user signup
3. Test preference updates from mobile app

### Week 3: Notifications
1. Set up background job system (Celery/Bull/Cron)
2. Implement meal reminder job
3. Implement water reminder job
4. Implement sleep reminder job
5. Test notifications end-to-end

## Mobile Integration Checklist

### Mobile Team Must:
- [x] Send FCM token to backend on app startup (already done)
- [x] Handle token refresh and re-register (already done)
- [ ] Call POST `/api/v1/notifications/tokens` on login
- [ ] Call DELETE `/api/v1/notifications/tokens` on logout
- [ ] Sync notification preferences with backend
- [ ] Handle deep-link navigation when notification is tapped

### Backend Team Must:
- [ ] Create 2 database tables
- [ ] Implement 4 API endpoints
- [ ] Set up Firebase Admin SDK
- [ ] Create 3 background jobs for scheduling
- [ ] Test with mobile app

## Testing

1. **Token Registration:** Register token from mobile → Check database
2. **Send Test Notification:** Use Firebase Console or backend script → Verify delivery
3. **Preference Update:** Change preferences in mobile → Verify in database
4. **Scheduled Notification:** Set meal time to current time + 2 minutes → Wait and verify delivery

## Important Notes

- **Timezone:** User timezone is stored in `users.timezone` column (IANA format, default 'UTC'). Convert `*_time_minutes` to user's local time when scheduling notifications (Phase 2).
- **Rate Limiting:** Don't send same notification type more than once per hour per user
- **Invalid Tokens:** Set `is_active = false` when FCM returns invalid token error
- **Default Preferences:** Create default preferences when user signs up:
  - Breakfast: 480 (8:00 AM)
  - Lunch: 720 (12:00 PM)
  - Dinner: 1080 (6:00 PM)
  - Water interval: 2 hours
  - Sleep: 1320 (10:00 PM)

## Security

1. Require JWT authentication on all endpoints
2. Users can only manage their own tokens/preferences
3. Validate FCM token format before storing
4. Don't log user data or notification content

## Production Checklist

- [x] Firebase Admin SDK service account key configured
- [x] Database tables created
- [x] All 4 API endpoints working
- [x] Background jobs running and scheduled
- [x] Mobile app successfully receives notifications
- [x] Token cleanup for invalid tokens working
