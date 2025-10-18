"""
Notification service for sending push notifications.
"""
import logging
from typing import Dict, List, Optional, Any

from src.domain.model.notification import (
    NotificationType,
    PushNotification,
    UserFcmToken,
    NotificationPreferences
)
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications."""
    
    def __init__(
        self,
        notification_repository: NotificationRepositoryPort,
        firebase_service
    ):
        self.notification_repository = notification_repository
        self.firebase_service = firebase_service
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: NotificationType,
        data: Optional[Dict[str, str]] = None
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
            tokens = self.notification_repository.find_active_fcm_tokens_by_user(user_id)
            
            if not tokens:
                logger.warning(f"No active FCM tokens found for user {user_id}")
                return {"success": False, "reason": "no_tokens"}
            
            # 2. Check if notification type is enabled for user
            preferences = self.notification_repository.find_notification_preferences_by_user(user_id)
            
            if preferences and not preferences.is_notification_type_enabled(notification_type):
                logger.info(f"Notification type {notification_type} is disabled for user {user_id}")
                return {"success": False, "reason": "disabled"}
            
            # 3. Send notification via Firebase
            fcm_tokens = [token.fcm_token for token in tokens]
            
            result = self.firebase_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                notification_type=str(notification_type),
                data=data,
                tokens=fcm_tokens
            )
            
            # 4. Handle invalid tokens
            if result.get("success") and result.get("failed_tokens"):
                await self._handle_failed_tokens(result["failed_tokens"])
            
            logger.info(f"Notification sent to user {user_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}
    
    async def send_meal_reminder(
        self,
        user_id: str,
        meal_type: str
    ) -> Dict[str, Any]:
        """Send meal reminder notification."""
        meal_titles = {
            "breakfast": "🍳 Breakfast Time!",
            "lunch": "🥗 Lunch Time!",
            "dinner": "🍽️ Dinner Time!"
        }
        
        meal_bodies = {
            "breakfast": "Start your day right - log your breakfast",
            "lunch": "Time for a nutritious lunch break",
            "dinner": "Wind down with a healthy dinner"
        }
        
        title = meal_titles.get(meal_type, "🍽️ Meal Time!")
        body = meal_bodies.get(meal_type, "Time to log your meal")
        
        notification_type = NotificationType(f"meal_reminder_{meal_type}")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            data={"meal_type": meal_type}
        )
    
    async def send_water_reminder(self, user_id: str) -> Dict[str, Any]:
        """Send water reminder notification."""
        return await self.send_notification(
            user_id=user_id,
            title="💧 Hydration Check",
            body="Time to drink some water!",
            notification_type=NotificationType.WATER_REMINDER,
            data={"type": "water_reminder"}
        )
    
    async def send_sleep_reminder(self, user_id: str) -> Dict[str, Any]:
        """Send sleep reminder notification."""
        return await self.send_notification(
            user_id=user_id,
            title="😴 Sleep Time",
            body="Get ready for a good night's rest",
            notification_type=NotificationType.SLEEP_REMINDER,
            data={"type": "sleep_reminder"}
        )
    
    async def send_progress_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send progress notification."""
        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=NotificationType.PROGRESS_NOTIFICATION,
            data=data
        )
    
    async def send_reengagement_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send reengagement notification."""
        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=NotificationType.REENGAGEMENT_NOTIFICATION,
            data=data
        )
    
    async def send_bulk_notifications(
        self,
        notifications: List[PushNotification]
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
                data=notification.data
            )
            results.append(result)
        
        return results
    
    async def _handle_failed_tokens(self, failed_tokens: List[Dict[str, Any]]):
        """Handle tokens that failed to receive notifications."""
        for failed_token in failed_tokens:
            token = failed_token["token"]
            error = failed_token["error"]
            
            # Check if it's an invalid token error
            if error in ["invalid-registration-token", "registration-token-not-registered"]:
                logger.info(f"Deactivating invalid FCM token: {token}")
                self.notification_repository.deactivate_fcm_token(token)
            else:
                logger.warning(f"FCM token failed with error {error}: {token}")
    
    def get_notification_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """Get notification preferences for user."""
        return self.notification_repository.find_notification_preferences_by_user(user_id)
    
    def is_notification_enabled(self, user_id: str, notification_type: NotificationType) -> bool:
        """Check if a notification type is enabled for user."""
        preferences = self.get_notification_preferences(user_id)
        if not preferences:
            return True  # Default to enabled if no preferences exist
        
        return preferences.is_notification_type_enabled(notification_type)
