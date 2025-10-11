"""
Service for orchestrating notification dispatch across channels.
"""
import logging
from typing import Dict, List, Any, Optional

from src.domain.model.notification import Notification
from src.app.services.notification_preference_service import NotificationPreferenceService
from src.app.services.push_notification_service import PushNotificationService
from src.app.services.email_notification_service import EmailNotificationService

logger = logging.getLogger(__name__)


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
        notification: Notification,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Dispatch notification to all enabled channels
        
        Args:
            user_id: User ID
            notification: Notification to send
            user_email: User email (required for email notifications)
            user_name: User name (for email personalization)
            
        Returns:
            Dict with 'push' and 'email' keys containing notification log IDs
        """
        results = {
            'push': [],
            'email': []
        }
        
        try:
            # Check if notifications are enabled
            preferences = await self.preference_service.get_preferences(user_id)
            
            if not preferences or not preferences.notifications_enabled:
                logger.info(f"Notifications disabled for user {user_id}")
                return results
            
            # Send push notification if enabled
            if notification.delivery_method == 'push' and preferences.can_send_push():
                try:
                    notification_ids = await self.push_service.send_push_notification(
                        user_id, notification
                    )
                    results['push'] = notification_ids
                    logger.info(f"Sent {len(notification_ids)} push notifications to user {user_id}")
                except Exception as e:
                    logger.error(f"Push notification failed for user {user_id}: {e}")
            
            # Send email notification if enabled
            if notification.delivery_method == 'email' and preferences.can_send_email():
                if not user_email:
                    logger.warning(f"User email required for email notification, skipping for user {user_id}")
                else:
                    try:
                        notification_id = await self.email_service.send_email_notification(
                            user_email=user_email,
                            user_name=user_name or user_email,
                            notification=notification
                        )
                        results['email'] = [notification_id]
                        logger.info(f"Sent email notification to user {user_id}")
                    except Exception as e:
                        logger.error(f"Email notification failed for user {user_id}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error dispatching notification for user {user_id}: {e}")
            return results
    
    async def dispatch_to_multiple_users(
        self,
        user_ids: List[str],
        notification_template: Notification,
        user_data: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dispatch notification to multiple users
        
        Args:
            user_ids: List of user IDs
            notification_template: Notification template
            user_data: Optional dict mapping user_id to user data (email, name)
            
        Returns:
            Dict with dispatch statistics
        """
        user_data = user_data or {}
        total_users = len(user_ids)
        successful = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                user_info = user_data.get(user_id, {})
                
                # Create notification for this user
                notification = Notification(
                    user_id=user_id,
                    notification_type=notification_template.notification_type,
                    delivery_method=notification_template.delivery_method,
                    title=notification_template.title,
                    body=notification_template.body,
                    data=notification_template.data
                )
                
                await self.dispatch_notification(
                    user_id=user_id,
                    notification=notification,
                    user_email=user_info.get('email'),
                    user_name=user_info.get('name')
                )
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to dispatch to user {user_id}: {e}")
                failed += 1
        
        results = {
            'total': total_users,
            'successful': successful,
            'failed': failed
        }
        
        logger.info(f"Batch dispatch complete: {results}")
        return results


from typing import Optional

