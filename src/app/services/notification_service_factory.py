"""
Factory for creating notification services with proper configuration.
Centralizes FCM credentials and SMTP configuration injection.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.notification_config import get_notification_config
from src.app.services.notification_preference_service import NotificationPreferenceService
from src.app.services.push_notification_service import PushNotificationService
from src.app.services.email_notification_service import EmailNotificationService
from src.app.services.notification_dispatch_service import NotificationDispatchService
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)

logger = logging.getLogger(__name__)


class NotificationServiceFactory:
    """Factory for creating notification services"""
    
    @staticmethod
    def create_preference_service(session: AsyncSession) -> NotificationPreferenceService:
        """Create notification preference service"""
        return NotificationPreferenceService(session)
    
    @staticmethod
    def create_push_service(session: AsyncSession) -> PushNotificationService:
        """
        Create push notification service with FCM credentials from configuration
        """
        config = get_notification_config()
        device_repo = DeviceTokenRepository(session)
        notif_repo = NotificationLogRepository(session)
        
        return PushNotificationService(
            device_repository=device_repo,
            notification_repository=notif_repo,
            fcm_credentials_path=config.fcm_credentials_path
        )
    
    @staticmethod
    def create_email_service(session: AsyncSession) -> EmailNotificationService:
        """
        Create email notification service with SMTP config from configuration
        """
        config = get_notification_config()
        notif_repo = NotificationLogRepository(session)
        
        return EmailNotificationService(
            notification_repository=notif_repo,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_username=config.smtp_username,
            smtp_password=config.smtp_password,
            smtp_use_tls=config.smtp_use_tls,
            from_email=config.email_from_address,
            from_name=config.email_from_name
        )
    
    @staticmethod
    def create_dispatch_service(session: AsyncSession) -> NotificationDispatchService:
        """
        Create notification dispatch service with all sub-services
        """
        preference_service = NotificationServiceFactory.create_preference_service(session)
        push_service = NotificationServiceFactory.create_push_service(session)
        email_service = NotificationServiceFactory.create_email_service(session)
        
        return NotificationDispatchService(
            preference_service=preference_service,
            push_service=push_service,
            email_service=email_service
        )
    
    @staticmethod
    def log_service_status():
        """Log the status of notification services"""
        config = get_notification_config()
        
        logger.info("=== Notification Services Status ===")
        
        # Check FCM
        if config.fcm_credentials_path:
            logger.info("✅ Push Notifications: ENABLED")
        else:
            logger.warning("⚠️  Push Notifications: DISABLED (no FCM credentials)")
        
        # Check Email
        if config.smtp_host and config.smtp_username:
            logger.info("✅ Email Notifications: ENABLED")
        else:
            logger.warning("⚠️  Email Notifications: DISABLED (no SMTP configuration)")
        
        logger.info("=" * 50)


# Convenience function for dependency injection
def get_dispatch_service(session: AsyncSession) -> NotificationDispatchService:
    """Get notification dispatch service (for FastAPI dependencies)"""
    return NotificationServiceFactory.create_dispatch_service(session)

