"""
Handler for getting notification preferences.
"""
import logging
from typing import Any, Dict, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.notification import GetNotificationPreferencesQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.notification import NotificationPreferences
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetNotificationPreferencesQuery)
class GetNotificationPreferencesQueryHandler(EventHandler[GetNotificationPreferencesQuery, Dict[str, Any]]):
    """Handler for getting notification preferences."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        pass

    async def handle(self, query: GetNotificationPreferencesQuery) -> Dict[str, Any]:
        """Handle notification preferences query."""
        cache_key, ttl = CacheKeys.notification_prefs(query.user_id)
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached is not None:
                return cached
        result = await self._compute(query)
        if self.cache_service:
            await self.cache_service.set_json(cache_key, result, ttl)
        return result

    async def _compute(self, query: GetNotificationPreferencesQuery) -> Dict[str, Any]:
        """Fetch notification preferences from DB."""
        try:
            with UnitOfWork() as uow:
                # Get preferences for user
                preferences = uow.notifications.find_notification_preferences_by_user(query.user_id)

                if not preferences:
                    # Create and return default preferences
                    default_prefs = NotificationPreferences.create_default(query.user_id)
                    saved_prefs = uow.notifications.save_notification_preferences(default_prefs)
                    uow.commit()

                    logger.info(f"Created default notification preferences for user {query.user_id}")
                    return saved_prefs.to_dict()
                else:
                    return preferences.to_dict()
        except Exception as e:
            logger.error(f"Error getting notification preferences: {e}")
            raise