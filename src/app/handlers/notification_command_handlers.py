"""
Command handlers for notification operations.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.commands.notification import (
    UpdateNotificationPreferencesCommand,
    RegisterDeviceTokenCommand,
    UnregisterDeviceTokenCommand,
    SendTestNotificationCommand
)
from src.app.services.notification_service_factory import NotificationServiceFactory
from src.domain.model.notification import Notification, NotificationPreferences
from src.infra.repositories.notification_repository import DeviceTokenRepository

logger = logging.getLogger(__name__)


class UpdateNotificationPreferencesCommandHandler:
    """Handler for updating notification preferences"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = NotificationServiceFactory.create_preference_service(db)
    
    async def handle(self, command: UpdateNotificationPreferencesCommand) -> NotificationPreferences:
        """Handle update notification preferences command"""
        logger.info(f"Updating notification preferences for user: {command.user_id}")
        
        # Get current preferences
        current_prefs = await self.service.get_preferences(command.user_id)
        if not current_prefs:
            raise ValueError("User profile not found")
        
        # Update preferences
        updated_prefs = await self.service.update_preferences(
            user_id=command.user_id,
            notifications_enabled=command.notifications_enabled,
            push_notifications_enabled=command.push_notifications_enabled,
            email_notifications_enabled=command.email_notifications_enabled,
            weekly_weight_reminder_enabled=command.weekly_weight_reminder_enabled,
            weekly_weight_reminder_day=command.weekly_weight_reminder_day,
            weekly_weight_reminder_time=command.weekly_weight_reminder_time
        )
        
        logger.info(f"Notification preferences updated successfully for user: {command.user_id}")
        return updated_prefs


class RegisterDeviceTokenCommandHandler:
    """Handler for registering device tokens"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DeviceTokenRepository(db)
    
    async def handle(self, command: RegisterDeviceTokenCommand):
        """Handle register device token command"""
        logger.info(f"Registering device for user: {command.user_id}")
        
        # Register or update device token
        device = await self.repository.register_device(
            user_id=command.user_id,
            device_token=command.device_token,
            platform=command.platform,
            device_info=command.device_info
        )
        
        logger.info(f"Device registered successfully: {device.id}")
        return device


class UnregisterDeviceTokenCommandHandler:
    """Handler for unregistering device tokens"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DeviceTokenRepository(db)
    
    async def handle(self, command: UnregisterDeviceTokenCommand) -> bool:
        """Handle unregister device token command"""
        logger.info(f"Unregistering device {command.device_id} for user: {command.user_id}")
        
        # Verify device belongs to user
        device = await self.repository.get_device_by_id(command.device_id)
        if not device:
            raise ValueError("Device not found")
        
        if device.user_id != command.user_id:
            raise PermissionError("Device does not belong to user")
        
        # Deactivate device
        success = await self.repository.deactivate_device(command.user_id, command.device_id)
        
        logger.info(f"Device unregistered successfully: {command.device_id}")
        return success


class SendTestNotificationCommandHandler:
    """Handler for sending test notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.push_service = NotificationServiceFactory.create_push_service(db)
    
    async def handle(self, command: SendTestNotificationCommand):
        """Handle send test notification command"""
        logger.info(f"Sending test notification to user: {command.user_id}")
        
        # Create test notification
        notification = Notification(
            user_id=command.user_id,
            notification_type=command.notification_type,
            delivery_method=command.delivery_method,
            title="Test Notification",
            body="This is a test notification from Nutree AI",
            data={"test": True}
        )
        
        # Send notification
        notification_ids = await self.push_service.send_push_notification(
            command.user_id,
            notification
        )
        
        logger.info(f"Test notification sent. IDs: {notification_ids}")
        return {
            "success": len(notification_ids) > 0,
            "message": "Test notification sent successfully" if notification_ids else "No devices found",
            "notification_ids": notification_ids
        }

