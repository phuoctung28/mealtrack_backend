# Scheduled Notification Service - Auto-Start Implementation

## Overview

The scheduled notification service now automatically starts when the application is built/started and stops gracefully when the application shuts down.

## Changes Made

### 1. Dependencies Setup (`src/api/base_dependencies.py`)

Added dependency injection functions for:
- **Firebase Service** - Singleton instance for push notifications
- **Notification Service** - Service for sending notifications
- **Scheduled Notification Service** - Service that runs on a schedule to send reminders

The scheduled notification service is initialized as a singleton during application startup using the `initialize_scheduled_notification_service()` function.

### 2. Application Lifecycle Integration (`src/api/main.py`)

Updated the FastAPI `lifespan` context manager to:

**On Startup:**
1. Run database migrations (existing)
2. Initialize the scheduled notification service
3. Start the service's background task loop
4. Log success/failure appropriately

**On Shutdown:**
1. Stop the scheduled notification service
2. Cancel all running tasks
3. Clean up resources

### 3. Test Endpoints (`src/api/routes/v1/notification_test.py`)

Enhanced the notification test endpoints to:

**POST `/v1/notification-test/send-test`**
- Actually sends a test notification via the scheduled notification service
- Returns detailed results about the notification delivery

**GET `/v1/notification-test/status`**
- Returns real-time status of:
  - Firebase initialization
  - Scheduled service running state
  - Overall system health

## How It Works

### Service Initialization Flow

```
App Startup
    ↓
Initialize Firebase Service (singleton)
    ↓
Initialize Notification Repository
    ↓
Initialize Notification Service
    ↓
Initialize Scheduled Notification Service
    ↓
Start background task (runs every 60 seconds)
    ↓
App Ready
```

### Background Task Loop

The scheduled notification service runs a background loop that:
1. Checks every 60 seconds
2. Gets current time in UTC
3. Checks for users who need:
   - Meal reminders (breakfast, lunch, dinner)
   - Sleep reminders
   - Water reminders (every 15 minutes)
4. Sends notifications based on user preferences

### Graceful Shutdown

On app shutdown:
1. Service sets `_running = False`
2. All async tasks are cancelled
3. Waits for tasks to complete (with exceptions)
4. Cleans up task list

## Testing the Implementation

### 1. Check Service Status

```bash
curl http://localhost:8000/v1/notification-test/status
```

Expected response:
```json
{
  "firebase_initialized": true,
  "scheduled_service_running": true,
  "scheduled_service_exists": true,
  "message": "Notification system is running",
  "status": "healthy"
}
```

### 2. Send Test Notification

```bash
curl -X POST http://localhost:8000/v1/notification-test/send-test \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id",
    "notification_type": "test"
  }'
```

Expected response:
```json
{
  "success": true,
  "message": "Test notification sent successfully to user test-user-id",
  "details": {
    "success": true,
    "sent": 1,
    "failed": 0
  }
}
```

### 3. Check Application Logs

When starting the application, you should see:

```
INFO: Starting MealTrack API...
INFO: Database migrations completed
INFO: Initializing scheduled notification service...
INFO: Starting scheduled notification service
INFO: Scheduled notification service started
INFO: Scheduled notification service started successfully!
INFO: MealTrack API started successfully!
```

When stopping the application:

```
INFO: Shutting down MealTrack API...
INFO: Stopping scheduled notification service...
INFO: Stopping scheduled notification service
INFO: Scheduled notification service stopped
INFO: Scheduled notification service stopped successfully!
```

## Configuration

### Environment Variables

The service uses the following environment variables:

- `FIREBASE_SERVICE_ACCOUNT_JSON` - Firebase service account credentials (JSON string)
- `FIREBASE_SERVICE_ACCOUNT_PATH` - Path to Firebase service account file (alternative to JSON string)
- `FAIL_ON_MIGRATION_ERROR` - Whether to fail app startup if migrations fail (default: false)

### Notification Scheduling

The service checks for notifications:
- **Every 60 seconds** for meal and sleep reminders
- **Every 15 minutes** for water reminders
- Times are matched based on user preferences in UTC

## Architecture Benefits

### 1. Automatic Management
- No manual service start required
- Service lifecycle tied to application lifecycle
- Graceful shutdown prevents orphaned tasks

### 2. Singleton Pattern
- Single service instance across the application
- Prevents duplicate notification sends
- Efficient resource usage

### 3. Dependency Injection
- Easy to test and mock
- Clean separation of concerns
- Can access service from any endpoint

### 4. Error Handling
- Service startup failures don't crash the app
- Background loop catches and logs exceptions
- Failed notifications are tracked and invalid tokens are cleaned up

## Troubleshooting

### Service Not Starting

1. **Check Firebase credentials:**
   ```bash
   echo $FIREBASE_SERVICE_ACCOUNT_JSON
   ```

2. **Check service status endpoint:**
   ```bash
   curl http://localhost:8000/v1/notification-test/status
   ```

3. **Check application logs for errors during startup**

### Notifications Not Sending

1. **Verify user has FCM tokens registered:**
   - Check the `user_fcm_tokens` table in the database

2. **Verify user notification preferences:**
   - Check the `notification_preferences` table
   - Ensure the notification type is enabled

3. **Check Firebase Admin SDK is initialized:**
   - Use the status endpoint
   - Look for Firebase initialization logs

### Service Not Stopping

If the service doesn't stop cleanly:
- Check for long-running tasks in the notification loop
- Verify asyncio task cancellation is working
- Look for deadlocks or blocking operations

## Future Enhancements

Potential improvements:
1. Add metrics/monitoring for notification sends
2. Implement notification rate limiting
3. Add support for timezone-aware scheduling
4. Support for dynamic schedule updates without restart
5. Add notification history/audit logging
6. Support for notification templates
7. A/B testing for notification content

## Related Files

- `src/api/main.py` - Application startup/shutdown
- `src/api/base_dependencies.py` - Dependency injection
- `src/infra/services/scheduled_notification_service.py` - Core service implementation
- `src/infra/services/firebase_service.py` - Firebase push notification handling
- `src/domain/services/notification_service.py` - Notification business logic
- `src/api/routes/v1/notification_test.py` - Testing endpoints

