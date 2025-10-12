"""
Service for sending push notifications via FCM and APNs.
"""
import logging
from typing import List, Optional
from datetime import datetime

# Firebase Admin SDK imports (will be installed as dependency)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not installed. Push notifications will not work.")

from src.domain.model.notification import Notification
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for sending push notifications"""
    
    def __init__(
        self,
        device_repository: DeviceTokenRepository,
        notification_repository: NotificationLogRepository,
        fcm_credentials_path: Optional[str] = None
    ):
        self.device_repository = device_repository
        self.notification_repository = notification_repository
        self.fcm_enabled = False
        
        # Initialize Firebase Admin SDK
        if FIREBASE_AVAILABLE and fcm_credentials_path:
            try:
                # Support multiple Firebase apps per environment
                # Check if default app exists, otherwise create it
                try:
                    firebase_admin.get_app()
                    self.fcm_enabled = True
                    logger.info("Using existing Firebase Admin SDK app")
                except ValueError:
                    # No app exists, create one
                    cred = credentials.Certificate(fcm_credentials_path)
                    firebase_admin.initialize_app(cred)
                    self.fcm_enabled = True
                    logger.info(f"Firebase Admin SDK initialized with credentials: {fcm_credentials_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                logger.warning("Push notifications will be disabled")
        else:
            logger.warning("FCM not initialized - push notifications disabled")
    
    async def send_push_notification(
        self,
        user_id: str,
        notification: Notification
    ) -> List[str]:
        """
        Send push notification to all user devices
        
        Args:
            user_id: User ID
            notification: Notification to send
            
        Returns:
            List of notification log IDs for sent notifications
        """
        if not self.fcm_enabled:
            logger.warning(f"Push notifications disabled - skipping for user {user_id}")
            return []
        
        # Get active devices for user
        devices = await self.device_repository.get_active_devices(user_id)
        
        if not devices:
            logger.info(f"No active devices for user {user_id}")
            return []
        
        sent_notification_ids = []
        
        for device in devices:
            log_id = None
            try:
                # Create notification log
                log_id = await self.notification_repository.create_log(
                    user_id=user_id,
                    notification=notification,
                    device_token_id=device.id
                )
                
                # Send to appropriate platform
                if device.platform == 'ios':
                    await self._send_to_apns(device.device_token, notification)
                elif device.platform == 'android' or device.platform == 'web':
                    await self._send_to_fcm(device.device_token, notification)
                else:
                    raise ValueError(f"Unsupported platform: {device.platform}")
                
                # Update log status
                await self.notification_repository.update_status(
                    log_id, 'sent', sent_at=datetime.utcnow()
                )
                
                # Update device last used
                await self.device_repository.update_last_used(device.id)
                
                sent_notification_ids.append(log_id)
                logger.info(f"Sent push notification to device {device.id}")
                
            except Exception as e:
                logger.error(f"Failed to send notification to device {device.id}: {e}")
                
                if log_id:
                    await self.notification_repository.update_status(
                        log_id, 'failed', error_message=str(e)
                    )
                
                # Mark device as inactive if token is invalid
                if self._is_invalid_token_error(e):
                    logger.warning(f"Marking device {device.id} as inactive due to invalid token")
                    await self.device_repository.mark_inactive(device.id)
        
        return sent_notification_ids
    
    async def _send_to_fcm(self, device_token: str, notification: Notification):
        """
        Send notification via Firebase Cloud Messaging
        
        Args:
            device_token: FCM device token
            notification: Notification to send
        """
        if not self.fcm_enabled:
            raise RuntimeError("FCM not initialized")
        
        try:
            # Build FCM message
            message = messaging.Message(
                token=device_token,
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data=self._serialize_data(notification.data),
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        channel_id=self._get_channel_id(notification.notification_type)
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.debug(f"FCM message sent successfully: {response}")
            
        except Exception as e:
            logger.error(f"FCM send error: {e}")
            raise
    
    async def _send_to_apns(self, device_token: str, notification: Notification):
        """
        Send notification via Apple Push Notification service
        
        Args:
            device_token: APNs device token
            notification: Notification to send
        """
        if not self.fcm_enabled:
            raise RuntimeError("FCM/APNs not initialized")
        
        try:
            # Build APNs payload
            message = messaging.Message(
                token=device_token,
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data=self._serialize_data(notification.data),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=notification.title,
                                body=notification.body
                            ),
                            sound='default',
                            badge=1,
                            category=self._get_category_id(notification.notification_type)
                        ),
                        custom_data=notification.data
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.debug(f"APNs message sent successfully: {response}")
            
        except Exception as e:
            logger.error(f"APNs send error: {e}")
            raise
    
    @staticmethod
    def _serialize_data(data: dict) -> dict:
        """Serialize data dict to string values (required by FCM)"""
        return {str(k): str(v) for k, v in data.items()}
    
    @staticmethod
    def _get_channel_id(notification_type: str) -> str:
        """Get Android notification channel ID for type"""
        channel_map = {
            'weight_reminder': 'reminders',
            'meal_reminder': 'reminders',
            'achievement': 'achievements',
            'goal_progress': 'progress',
            'social': 'social',
            'system': 'system'
        }
        return channel_map.get(notification_type, 'default')
    
    @staticmethod
    def _get_category_id(notification_type: str) -> str:
        """Get iOS notification category ID for type"""
        return notification_type.upper()
    
    @staticmethod
    def _is_invalid_token_error(error: Exception) -> bool:
        """Check if error indicates invalid device token"""
        error_str = str(error).lower()
        invalid_keywords = [
            'invalid',
            'unregistered',
            'notfound',
            'mismatchsenderid',
            'invalid-argument',
            'registration-token-not-registered'
        ]
        return any(keyword in error_str for keyword in invalid_keywords)

