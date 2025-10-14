"""
Notification system configuration.
"""
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationConfig:
    """Configuration for notification system"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        
        # FCM Configuration
        self.fcm_credentials_path = self._get_fcm_credentials_path()
        
        # SMTP Configuration
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.email_from_address = os.getenv('EMAIL_FROM_ADDRESS', 'noreply@nutreeai.com')
        self.email_from_name = os.getenv('EMAIL_FROM_NAME', 'Nutree AI')
        
        # Notification Settings
        self.notification_log_retention_days = int(os.getenv('NOTIFICATION_LOG_RETENTION_DAYS', '30'))
        self.device_token_inactivity_days = int(os.getenv('DEVICE_TOKEN_INACTIVITY_DAYS', '90'))
        
        self._log_configuration()
    
    def _get_fcm_credentials_path(self) -> Optional[str]:
        """
        Get FCM credentials path
        
        Priority:
        1. FCM_CREDENTIALS_PATH env variable (explicit path)
        2. Auto-detect credentials/firebase-credentials.json
        3. None (FCM disabled)
        """
        # Check for explicit path from environment variable
        explicit_path = os.getenv('FCM_CREDENTIALS_PATH')
        if explicit_path:
            if os.path.exists(explicit_path):
                return explicit_path
            else:
                logger.warning(f"FCM_CREDENTIALS_PATH specified but file not found: {explicit_path}")
        
        # Auto-detect default location
        credentials_dir = self.base_path / 'credentials'
        default_path = credentials_dir / 'firebase-credentials.json'
        
        if default_path.exists():
            logger.info(f"Auto-detected FCM credentials: {default_path}")
            return str(default_path)
        
        logger.warning("No FCM credentials found. Push notifications will be disabled.")
        logger.info("To enable push notifications, set FCM_CREDENTIALS_PATH or place credentials at: credentials/firebase-credentials.json")
        return None
    
    def _log_configuration(self):
        """Log current configuration (without sensitive data)"""
        logger.info("=== Notification Configuration ===")
        logger.info(f"FCM Enabled: {self.fcm_credentials_path is not None}")
        if self.fcm_credentials_path:
            logger.info(f"FCM Credentials: {self.fcm_credentials_path}")
        logger.info(f"SMTP Enabled: {self.smtp_host is not None}")
        if self.smtp_host:
            logger.info(f"SMTP Host: {self.smtp_host}:{self.smtp_port}")
            logger.info(f"Email From: {self.email_from_name} <{self.email_from_address}>")
        logger.info(f"Log Retention: {self.notification_log_retention_days} days")
        logger.info(f"Device Token Inactivity: {self.device_token_inactivity_days} days")
        logger.info("=" * 50)


# Global configuration instance
_notification_config: Optional[NotificationConfig] = None


def get_notification_config() -> NotificationConfig:
    """Get or create notification configuration"""
    global _notification_config
    if _notification_config is None:
        _notification_config = NotificationConfig()
    return _notification_config


def reload_notification_config() -> NotificationConfig:
    """Reload notification configuration (useful for tests)"""
    global _notification_config
    _notification_config = NotificationConfig()
    return _notification_config

