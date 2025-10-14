# Notification System Setup Guide

## Overview
This guide explains how to set up and configure the notification preferences system in the Nutree AI backend.

## Prerequisites
- Python 3.9+
- PostgreSQL database
- Firebase Admin SDK credentials (for push notifications)
- SMTP server credentials (for email notifications)

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

The notification system dependencies are already included in `requirements.txt`:
- `firebase-admin>=6.2.0` - Firebase Admin SDK for push notifications
- `apscheduler>=3.10.4` - Background job scheduler

### 2. Run Database Migration
```bash
# Run the migration to add notification tables and columns
alembic upgrade head
```

This will:
- Add notification preference columns to `user_profiles` table
- Create `device_tokens` table for push notification tokens
- Create `notification_logs` table for tracking sent notifications

### 3. Configure Environment Variables

Add the following to your `.env` file:

```env
# Firebase Cloud Messaging (FCM) Configuration
# Option 1: Specify explicit path
FCM_CREDENTIALS_PATH=/mealtrack_backend/credentials/firebase-credentials.json

# Option 2: Or place file at default location and it will be auto-detected
# credentials/firebase-credentials.json

# Email Notification Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM_ADDRESS=noreply@nutreeai.com
EMAIL_FROM_NAME=Nutree AI

# Notification Settings (optional, defaults shown)
NOTIFICATION_LOG_RETENTION_DAYS=30
DEVICE_TOKEN_INACTIVITY_DAYS=90
```

### 4. Firebase Setup

#### Get Firebase Credentials
1. Go to Firebase Console: https://console.firebase.google.com/
2. Select your project (e.g., `nutree-ai`)
3. Go to Project Settings > Service Accounts
4. Click "Generate New Private Key"
5. Download the JSON file and save it to:
   ```bash
   # Save to default location (auto-detected)
   mv ~/Downloads/nutree-ai-*.json credentials/firebase-credentials.json
   
   # Or save anywhere and set FCM_CREDENTIALS_PATH in .env
   ```

#### Configure Firebase Messaging
1. In Firebase Console, go to Cloud Messaging
2. Note your Server Key and Sender ID
3. Configure iOS APNs certificates if supporting iOS

### 5. Update Main Application

Add to your `src/api/main.py`:

```python
from src.api.routes.v1.notifications import router as notifications_router
from src.app.scheduler import notification_scheduler
from src.infra.database.config import get_async_session

# Include notification router
app.include_router(notifications_router)

# Initialize and start scheduler on startup
@app.on_event("startup")
async def startup_event():
    notification_scheduler.initialize(get_async_session)
    notification_scheduler.start()
    logger.info("Notification scheduler started")

# Shutdown scheduler on app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    notification_scheduler.shutdown()
    logger.info("Notification scheduler stopped")
```

## API Endpoints

### Notification Preferences
- `GET /api/v1/users/{user_id}/preferences/notifications` - Get preferences
- `PUT /api/v1/users/{user_id}/preferences/notifications` - Update preferences

### Device Token Management
- `POST /api/v1/users/{user_id}/devices` - Register device token
- `GET /api/v1/users/{user_id}/devices` - List user devices
- `DELETE /api/v1/users/{user_id}/devices/{device_id}` - Unregister device

### Notification History
- `GET /api/v1/users/{user_id}/notifications/history` - Get notification history

### Testing
- `POST /api/v1/users/{user_id}/notifications/test` - Send test notification

## Mobile App Integration

### iOS Configuration

In your iOS app, add Firebase SDK and request notification permissions:

```swift
import FirebaseMessaging
import UserNotifications

// Request notification permission
UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
    if granted {
        DispatchQueue.main.async {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }
}

// Get and send FCM token to backend
Messaging.messaging().token { token, error in
    if let token = token {
        // Send token to your backend
        registerDeviceToken(token: token, platform: "ios")
    }
}
```

### Android Configuration

In your Android app:

```kotlin
import com.google.firebase.messaging.FirebaseMessaging

// Get and send FCM token
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        // Send token to your backend
        registerDeviceToken(token, "android")
    }
}
```

### Flutter Configuration

```dart
import 'package:firebase_messaging/firebase_messaging.dart';

// Request permission
NotificationSettings settings = await FirebaseMessaging.instance.requestPermission(
  alert: true,
  badge: true,
  sound: true,
);

// Get FCM token
String? token = await FirebaseMessaging.instance.getToken();
if (token != null) {
  // Send to backend
  await registerDeviceToken(token, Platform.isIOS ? 'ios' : 'android');
}
```

## Background Jobs

### Weekly Weight Reminder Job
Runs every 5 minutes to check for users who need weight reminders.

- Checks user preferences for enabled reminders
- Sends notifications at configured day/time
- Calculates days since last weight update
- Dispatches via push or email based on preferences

### Job Monitoring

Check scheduler status:
```bash
# View scheduler logs
tail -f /var/log/nutree/scheduler.log

# Check job execution
grep "weekly_weight_reminder" /var/log/nutree/scheduler.log
```

## Testing

### Test Push Notifications
```bash
curl -X POST http://localhost:8000/api/v1/users/{user_id}/notifications/test \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "weight_reminder",
    "delivery_method": "push"
  }'
```

### Test Email Notifications
```bash
curl -X POST http://localhost:8000/api/v1/users/{user_id}/notifications/test \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "weight_reminder",
    "delivery_method": "email"
  }'
```

### Test Preference Updates
```bash
curl -X PUT http://localhost:8000/api/v1/users/{user_id}/preferences/notifications \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "notifications_enabled": true,
    "push_notifications_enabled": true,
    "email_notifications_enabled": false,
    "weekly_weight_reminder_enabled": true,
    "weekly_weight_reminder_day": 0,
    "weekly_weight_reminder_time": "09:00"
  }'
```

## Troubleshooting

### Push Notifications Not Working
1. Check Firebase credentials are valid
2. Verify device token is registered
3. Check user has notifications enabled in preferences
4. Verify platform (iOS/Android) is correctly set
5. Check Firebase Console for delivery logs

### Email Notifications Not Sending
1. Verify SMTP credentials are correct
2. Check user has email notifications enabled
3. Verify user email is valid and verified
4. Check SMTP server logs

### Scheduler Not Running
1. Check scheduler was initialized in main.py
2. Verify database connection is working
3. Check scheduler logs for errors
4. Ensure APScheduler is installed

### Device Token Errors
1. "Invalid token" - Device token may be expired, mark as inactive
2. "Token not found" - Device may not be registered
3. "Platform mismatch" - Verify platform matches token type

## Monitoring

### Key Metrics to Track
- Notification delivery rate (target: >95%)
- Push notification open rate
- Email notification open rate
- Device token registration rate
- Scheduler job execution time
- Failed notification count

### Alerts to Configure
- Notification delivery rate drops below 90%
- Scheduler job failures
- High error rate in notification logs
- Database connection issues

## Security Considerations

1. **Device Tokens**: Stored encrypted, invalidated after inactivity
2. **User Authorization**: Only users can modify their own preferences
3. **Rate Limiting**: Prevent notification spam
4. **Data Privacy**: Notification content sanitized, no sensitive data
5. **HTTPS**: All API communications encrypted

## Maintenance

### Regular Tasks
- Clean up old notification logs (automated, 30-day retention)
- Review inactive device tokens (90-day inactivity threshold)
- Monitor notification delivery metrics
- Update Firebase SDK regularly

### Database Maintenance
```sql
-- Clean up old notification logs (done automatically by job)
DELETE FROM notification_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Remove inactive device tokens
UPDATE device_tokens SET is_active = false 
WHERE last_used_at < NOW() - INTERVAL '90 days';
```

## Support

For issues or questions:
- Check logs: `/var/log/nutree/`
- Review Firebase Console
- Contact development team

---

Last Updated: 2025-10-11

