"""
Query handlers for notification operations.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.queries.notification import (
    GetNotificationPreferencesQuery,
    GetUserDevicesQuery,
    GetNotificationHistoryQuery
)
from src.app.services.notification_service_factory import NotificationServiceFactory
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)

logger = logging.getLogger(__name__)


class GetNotificationPreferencesQueryHandler:
    """Handler for getting notification preferences"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = NotificationServiceFactory.create_preference_service(db)
    
    async def handle(self, query: GetNotificationPreferencesQuery):
        """Handle get notification preferences query"""
        logger.info(f"Getting notification preferences for user: {query.user_id}")
        
        preferences = await self.service.get_preferences(query.user_id)
        if not preferences:
            raise ValueError("User profile not found")
        
        return preferences


class GetUserDevicesQueryHandler:
    """Handler for getting user devices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DeviceTokenRepository(db)
    
    async def handle(self, query: GetUserDevicesQuery):
        """Handle get user devices query"""
        logger.info(f"Getting devices for user: {query.user_id}")
        
        devices = await self.repository.get_active_devices_for_user(query.user_id)
        
        return devices


class GetNotificationHistoryQueryHandler:
    """Handler for getting notification history"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = NotificationLogRepository(db)
    
    async def handle(self, query: GetNotificationHistoryQuery):
        """Handle get notification history query"""
        logger.info(f"Getting notification history for user: {query.user_id}")
        
        logs, total = await self.repository.get_user_notification_history(
            user_id=query.user_id,
            notification_type=query.notification_type,
            limit=query.limit,
            offset=query.offset
        )
        
        return {
            "logs": logs,
            "total": total,
            "limit": query.limit,
            "offset": query.offset
        }

