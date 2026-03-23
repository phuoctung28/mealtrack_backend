"""
Notification service for sending push notifications.
"""

import logging
from typing import Dict, List, Optional, Any

from src.domain.model.notification import (
    NotificationType,
    PushNotification,
    NotificationPreferences,
)
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)

# FCM error codes that indicate token should be deactivated
DEACTIVATABLE_FCM_ERRORS = {
    "invalid-registration-token",
    "registration-token-not-registered",
    "NOT_FOUND",  # Firebase messaging.exceptions.NotFoundError
    "UNREGISTERED",  # Token unregistered from FCM
    "INVALID_ARGUMENT",  # Malformed token
    "UNAUTHENTICATED",  # Token from different Firebase project (e.g. debug build)
}

# Locale-keyed notification messages (EN default, VI supported)
# TODO: add more locales as needed
NOTIFICATION_MESSAGES = {
    "en": {
        "meal_reminder": {
            "breakfast": {"title": "🍳 Breakfast Time!", "body": "Start your day right - log your breakfast"},
            "lunch": {"title": "🥗 Lunch Time!", "body": "Time for a nutritious lunch break"},
            "dinner": {"title": "🍽️ Dinner Time!", "body": "Wind down with a healthy dinner"},
        },
        "daily_summary": {
            "zero_logs": {"title": "📝 Log Your Meals", "body": "No meals logged today. Add them from memory to track your progress!"},
            "on_target": {"title": "🎉 Great Job Today!", "body_template": "You hit {percentage}% of your calorie goal. View your daily success!"},
            "under_goal": {"title": "📊 Daily Summary", "body_template": "You're {deficit} cal short today. Consider a healthy snack!"},
            "slightly_over": {"title": "💡 Daily Summary", "body_template": "You went {excess} cal over today. No worries - track carefully tomorrow!"},
            "way_over": {"title": "📝 Daily Summary", "body_template": "You went {excess} cal over today. Stay mindful - tomorrow is a fresh start!"},
        },
    },
    "vi": {
        "meal_reminder": {
            "breakfast": {"title": "🍳 Giờ ăn sáng!", "body": "Bắt đầu ngày mới — ghi lại bữa sáng nhé"},
            "lunch": {"title": "🥗 Giờ ăn trưa!", "body": "Nghỉ trưa bổ dưỡng nào"},
            "dinner": {"title": "🍽️ Giờ ăn tối!", "body": "Thư giãn với bữa tối lành mạnh nhé"},
        },
        "daily_summary": {
            "zero_logs": {"title": "📝 Ghi lại bữa ăn", "body": "Hôm nay chưa ghi bữa nào. Thêm từ trí nhớ để theo dõi tiến trình!"},
            "on_target": {"title": "🎉 Tuyệt vời!", "body_template": "Bạn đạt {percentage}% mục tiêu calo. Xem thành tích!"},
            "under_goal": {"title": "📊 Tổng kết ngày", "body_template": "Bạn thiếu {deficit} cal hôm nay. Ăn nhẹ gì đi!"},
            "slightly_over": {"title": "💡 Tổng kết ngày", "body_template": "Bạn vượt {excess} cal hôm nay. Không sao — mai cố gắng hơn!"},
            "way_over": {"title": "📝 Tổng kết ngày", "body_template": "Bạn vượt {excess} cal hôm nay. Chú ý hơn — ngày mai là khởi đầu mới!"},
        },
    },
}


def _get_messages(language: str) -> dict:
    """Get notification messages for language, fallback to EN."""
    return NOTIFICATION_MESSAGES.get(language, NOTIFICATION_MESSAGES["en"])


class NotificationService:
    """Service for sending push notifications."""

    def __init__(
        self, notification_repository: NotificationRepositoryPort, firebase_service
    ):
        self.notification_repository = notification_repository
        self.firebase_service = firebase_service

    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: NotificationType,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to user.

        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            notification_type: Type of notification
            data: Optional data payload

        Returns:
            Dictionary with success status and results
        """
        try:
            # 1. Get user's active FCM tokens
            tokens = self.notification_repository.find_active_fcm_tokens_by_user(
                user_id
            )

            if not tokens:
                logger.warning(f"No active FCM tokens found for user {user_id}")
                return {"success": False, "reason": "no_tokens"}

            # 2. Check if notification type is enabled for user
            preferences = (
                self.notification_repository.find_notification_preferences_by_user(
                    user_id
                )
            )

            if preferences and not preferences.is_notification_type_enabled(
                notification_type
            ):
                logger.info(
                    f"Notification type {notification_type} is disabled for user {user_id}"
                )
                return {"success": False, "reason": "disabled"}

            # 3. Send notification via Firebase
            fcm_tokens = [token.fcm_token for token in tokens]

            result = self.firebase_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                notification_type=str(notification_type),
                data=data,
                tokens=fcm_tokens,
            )

            # 4. Handle invalid tokens
            if result.get("success") and result.get("failed_tokens"):
                await self._handle_failed_tokens(
                    result["failed_tokens"],
                    user_id=user_id,
                    notification_type=str(notification_type),
                )

            logger.info(f"Notification sent to user {user_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}

    async def send_meal_reminder(
        self, user_id: str, meal_type: str, language: str = "en"
    ) -> Dict[str, Any]:
        """Send meal reminder notification in user's preferred language."""
        messages = _get_messages(language)["meal_reminder"]
        config = messages.get(
            meal_type, {"title": "🍽️ Meal Time!", "body": "Time to log your meal"}
        )

        notification_type = NotificationType(f"meal_reminder_{meal_type}")

        return await self.send_notification(
            user_id=user_id,
            title=config["title"],
            body=config["body"],
            notification_type=notification_type,
            data={"meal_type": meal_type},
        )

    async def send_daily_summary(
        self,
        user_id: str,
        calories_consumed: float,
        calorie_goal: float,
        meals_logged: int,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Send daily summary notification in user's preferred language."""
        title, body = self._get_summary_message(
            calories_consumed, calorie_goal, meals_logged, language=language
        )

        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=NotificationType.DAILY_SUMMARY,
            data={
                "type": "daily_summary",
                "calories_consumed": str(int(calories_consumed)),
                "calorie_goal": str(int(calorie_goal)),
                "meals_logged": str(meals_logged),
            },
        )

    def _get_summary_message(
        self, consumed: float, goal: float, meals_logged: int,
        language: str = "en",
    ) -> tuple[str, str]:
        """Get title and body for summary based on consumption level and language."""
        summary = _get_messages(language)["daily_summary"]

        if meals_logged == 0:
            cfg = summary["zero_logs"]
            return cfg["title"], cfg["body"]

        percentage = (consumed / goal) * 100 if goal > 0 else 0

        if 95 <= percentage <= 105:  # ±5%
            cfg = summary["on_target"]
            return cfg["title"], cfg["body_template"].format(percentage=int(percentage))
        elif percentage < 95:
            deficit = int(goal - consumed)
            cfg = summary["under_goal"]
            return cfg["title"], cfg["body_template"].format(deficit=deficit)
        elif 105 < percentage <= 120:  # 10-20% over
            excess = int(consumed - goal)
            cfg = summary["slightly_over"]
            return cfg["title"], cfg["body_template"].format(excess=excess)
        else:  # 20%+ over
            excess = int(consumed - goal)
            cfg = summary["way_over"]
            return cfg["title"], cfg["body_template"].format(excess=excess)

    async def send_bulk_notifications(
        self, notifications: List[PushNotification]
    ) -> List[Dict[str, Any]]:
        """
        Send multiple notifications efficiently.

        Args:
            notifications: List of push notifications to send

        Returns:
            List of results for each notification
        """
        results = []

        for notification in notifications:
            result = await self.send_notification(
                user_id=notification.user_id,
                title=notification.title,
                body=notification.body,
                notification_type=notification.notification_type,
                data=notification.data,
            )
            results.append(result)

        return results

    async def _handle_failed_tokens(
        self,
        failed_tokens: List[Dict[str, Any]],
        user_id: str = "",
        notification_type: str = "",
    ):
        """Handle tokens that failed to receive notifications."""
        deactivated_count = 0
        context = f"user={user_id}, type={notification_type}" if user_id else ""

        for failed_token in failed_tokens:
            token = failed_token["token"]
            error = failed_token.get("error", "unknown")
            error_upper = str(error).upper()

            # Check if error warrants token deactivation
            should_deactivate = any(
                err_code in error_upper for err_code in DEACTIVATABLE_FCM_ERRORS
            )

            if should_deactivate:
                logger.info(
                    f"Deactivating invalid FCM token ({context}): "
                    f"{token[:20]}... error={error}"
                )
                self.notification_repository.deactivate_fcm_token(token)
                deactivated_count += 1
            else:
                logger.warning(
                    f"FCM token failed ({context}) with error {error}: {token[:20]}..."
                )

        if deactivated_count > 0:
            logger.info(
                f"Deactivated {deactivated_count} invalid FCM tokens ({context})"
            )

    def get_notification_preferences(
        self, user_id: str
    ) -> Optional[NotificationPreferences]:
        """Get notification preferences for user."""
        return self.notification_repository.find_notification_preferences_by_user(
            user_id
        )

    def is_notification_enabled(
        self, user_id: str, notification_type: NotificationType
    ) -> bool:
        """Check if a notification type is enabled for user."""
        preferences = self.get_notification_preferences(user_id)
        if not preferences:
            return True  # Default to enabled if no preferences exist

        return preferences.is_notification_type_enabled(notification_type)
