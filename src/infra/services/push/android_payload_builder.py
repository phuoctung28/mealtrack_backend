"""Android FCM payload builder for high-importance notifications.

Channel IDs match the mobile app's `NotificationChannelConfig.forPriority`
mapping; mobile creates the channels with matching IDs at app start.
"""

from firebase_admin import messaging

HIGH_PRIORITY_CHANNEL_ID = "meal_reminders"
MEDIUM_PRIORITY_CHANNEL_ID = "daily_summary"


def build_android_config(
    channel_id: str = HIGH_PRIORITY_CHANNEL_ID,
) -> messaging.AndroidConfig:
    """Build Android config for high-priority notification (heads-up display)."""
    return messaging.AndroidConfig(
        priority="high",
        notification=messaging.AndroidNotification(
            channel_id=channel_id,
            sound="default",
        ),
    )
