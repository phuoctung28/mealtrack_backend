"""
Query handlers for notification operations.
"""
import logging
from typing import Any, Dict

from src.app.queries.notification import GetNotificationPreferencesQuery
from src.domain.model.notification import NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


class GetNotificationPreferencesQueryHandler:
    """Handler for getting notification preferences."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort):
        self.notification_repository = notification_repository
    
    async def handle(self, query: GetNotificationPreferencesQuery) -> Dict[str, Any]:
        """Handle notification preferences query."""
        try:
            # Get preferences for user
            preferences = self.notification_repository.find_notification_preferences_by_user(query.user_id)
            
            if not preferences:
                # Create and return default preferences
                default_prefs = NotificationPreferences.create_default(query.user_id)
                saved_prefs = self.notification_repository.save_notification_preferences(default_prefs)
                
                logger.info(f"Created default notification preferences for user {query.user_id}")
                return saved_prefs.to_dict()
            else:
                return preferences.to_dict()
        except Exception as e:
            logger.error(f"Error getting notification preferences: {e}")
            raise e
