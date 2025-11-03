#!/usr/bin/env python3
"""
Test script to spam notifications for a specific user every 10 seconds.
This is for testing notification functionality.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infra.database.config import SessionLocal
from src.infra.database.models.notification.notification_preferences import NotificationPreferences as DBNotificationPreferences
# Import all models to ensure SQLAlchemy relationships are registered
from src.infra.database.models.user.user import User
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.notification import UserFcmToken
from src.infra.repositories.notification_repository import NotificationRepository
from src.domain.services.notification_service import NotificationService
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService
from src.domain.model.notification import NotificationType


async def setup_test_user_preferences(user_id: str, session):
    """Set up notification preferences for the test user."""
    print(f"\n=== Setting up notification preferences for user: {user_id} ===")
    
    # First, check if the user exists
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        print(f"\n❌ ERROR: User {user_id} not found in database!")
        print(f"   The user needs to sign in to the app at least once to create their account.")
        print(f"   Or you can use an existing user from the database.\n")
        # Show some existing users
        existing_users = session.query(User).limit(5).all()
        if existing_users:
            print(f"📋 Found {len(existing_users)} existing users (showing up to 5):")
            for u in existing_users:
                print(f"   - ID: {u.id}")
                print(f"     Email: {u.email or 'N/A'}")
                print(f"     Name: {u.display_name or 'N/A'}\n")
        return False
    
    print(f"✅ User exists: {user.email or user.display_name or user.id}")
    
    # Check if preferences already exist
    existing = session.query(DBNotificationPreferences).filter_by(user_id=user_id).first()
    
    if existing:
        print(f"Found existing preferences for user {user_id}")
        # Enable all notification types
        existing.meal_reminders_enabled = True
        existing.water_reminders_enabled = True
        existing.sleep_reminders_enabled = True
        existing.progress_notifications_enabled = True
        existing.reengagement_notifications_enabled = True
        session.commit()
        print("✅ Updated existing preferences - all notification types enabled")
    else:
        print(f"Creating new preferences for user {user_id}")
        import uuid
        new_prefs = DBNotificationPreferences(
            id=str(uuid.uuid4()),
            user_id=user_id,
            meal_reminders_enabled=True,
            water_reminders_enabled=True,
            sleep_reminders_enabled=True,
            progress_notifications_enabled=True,
            reengagement_notifications_enabled=True,
            breakfast_time_minutes=480,  # 8:00 AM
            lunch_time_minutes=720,      # 12:00 PM
            dinner_time_minutes=1080,    # 6:00 PM
            sleep_reminder_time_minutes=1320,  # 10:00 PM
            water_reminder_interval_hours=2
        )
        session.add(new_prefs)
        session.commit()
        print("✅ Created new preferences - all notification types enabled")
    
    return True


async def spam_notifications(user_id: str, interval_seconds: int = 10, count: int = 100):
    """Send test notifications to a user every X seconds."""
    print(f"\n=== Starting notification spam test ===")
    print(f"Target User: {user_id}")
    print(f"Interval: {interval_seconds} seconds")
    print(f"Total notifications: {count}")
    print(f"Press Ctrl+C to stop\n")
    
    # Set up database connection
    session = SessionLocal()
    
    try:
        # Set up notification preferences
        setup_success = await setup_test_user_preferences(user_id, session)
        if not setup_success:
            return
        
        # Initialize notification services
        notification_repo = NotificationRepository(session)
        firebase_service = FirebaseService()
        notification_service = NotificationService(notification_repo, firebase_service)
        scheduled_service = ScheduledNotificationService(notification_repo, notification_service)
        
        # Check if user has FCM tokens
        tokens = notification_repo.find_active_fcm_tokens_by_user(user_id)
        if not tokens:
            print(f"\n⚠️  WARNING: User {user_id} has no active FCM tokens!")
            print("   The notifications will be sent but may not be delivered.")
            print("   Make sure the user has registered their device token.\n")
        else:
            print(f"✅ Found {len(tokens)} active FCM token(s) for user")
            for token in tokens:
                print(f"   - {token.device_type.value}: {token.fcm_token[:20]}...")
        
        # Send notifications
        notification_types = [
            ("Test", NotificationType.PROGRESS_NOTIFICATION),
            ("Meal Reminder", NotificationType.MEAL_REMINDER_BREAKFAST),
            ("Water Reminder", NotificationType.WATER_REMINDER),
            ("Sleep Reminder", NotificationType.SLEEP_REMINDER),
        ]
        
        sent_count = 0
        failed_count = 0
        
        for i in range(count):
            try:
                # Rotate through different notification types
                notif_name, notif_type = notification_types[i % len(notification_types)]
                
                # Get emoji based on type
                emojis = {
                    "Test": "🧪",
                    "Meal Reminder": "🍽️",
                    "Water Reminder": "💧",
                    "Sleep Reminder": "😴"
                }
                emoji = emojis.get(notif_name, "🔔")
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                result = await notification_service.send_notification(
                    user_id=user_id,
                    title=f"{emoji} {notif_name} #{i+1}",
                    body=f"Test notification sent at {timestamp}",
                    notification_type=notif_type,
                    data={
                        "type": "test",
                        "sequence": i + 1,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                if result.get("success"):
                    sent_count += 1
                    print(f"[{timestamp}] ✅ Sent #{i+1}/{count} - {notif_name} - {result.get('message', 'Success')}")
                else:
                    failed_count += 1
                    print(f"[{timestamp}] ❌ Failed #{i+1}/{count} - {result.get('error', 'Unknown error')}")
                
                # Wait before sending next notification
                if i < count - 1:  # Don't wait after the last one
                    await asyncio.sleep(interval_seconds)
                    
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                failed_count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error sending notification #{i+1}: {e}")
                await asyncio.sleep(interval_seconds)
        
        # Summary
        print(f"\n=== Test Complete ===")
        print(f"✅ Sent: {sent_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Success Rate: {(sent_count / (sent_count + failed_count) * 100):.1f}%")
        
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Spam test notifications for a user')
    parser.add_argument('user_id', help='Firebase user ID to send notifications to')
    parser.add_argument('--interval', type=int, default=10, help='Interval between notifications in seconds (default: 10)')
    parser.add_argument('--count', type=int, default=100, help='Number of notifications to send (default: 100)')
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(spam_notifications(args.user_id, args.interval, args.count))


if __name__ == "__main__":
    main()

