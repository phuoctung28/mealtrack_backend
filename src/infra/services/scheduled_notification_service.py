"""
Scheduled notification service for sending push notifications at specific times.
"""
import asyncio
import logging
from datetime import datetime

from src.domain.services.timezone_utils import utc_now, timezone
from typing import Dict, List

from src.domain.model.notification import NotificationType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ScheduledNotificationService:
    """Service for scheduling and sending notifications at specific times."""

    # Scheduling constants
    SCHEDULING_LOOP_INTERVAL_SECONDS = 60
    SCHEDULING_LOOP_ERROR_RETRY_SECONDS = 30
    WATER_REMINDER_MAX_BATCH_SIZE = 10

    def __init__(
        self,
        notification_repository: NotificationRepositoryPort,
        notification_service: NotificationService
    ):
        self.notification_repository = notification_repository
        self.notification_service = notification_service
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start the scheduled notification service."""
        if self._running:
            logger.warning("Scheduled notification service is already running")
            return
        
        self._running = True
        logger.info("Starting scheduled notification service")
        
        # Start the main scheduling loop
        task = asyncio.create_task(self._scheduling_loop())
        self._tasks.append(task)
        
        logger.info("Scheduled notification service started")
    
    async def stop(self):
        """Stop the scheduled notification service."""
        if not self._running:
            logger.warning("Scheduled notification service is not running")
            return
        
        self._running = False
        logger.info("Stopping scheduled notification service")
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("Scheduled notification service stopped")
    
    async def _scheduling_loop(self):
        """Main scheduling loop that runs every minute."""
        while self._running:
            try:
                current_time = datetime.now(timezone.utc)
                await self._check_and_send_notifications(current_time)

                # Wait for next check
                await asyncio.sleep(self.SCHEDULING_LOOP_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                logger.info("Scheduling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(self.SCHEDULING_LOOP_ERROR_RETRY_SECONDS)
    
    async def _check_and_send_notifications(self, current_time: datetime):
        """Check if any notifications need to be sent at the current time."""
        try:
            # Check meal reminders (pass full datetime)
            await self._check_meal_reminders(current_time)

            # Check sleep reminders (pass full datetime)
            await self._check_sleep_reminders(current_time)

            # Check water reminders (based on user intervals)
            await self._check_water_reminders(current_time)
                
        except Exception as e:
            logger.error(f"Error checking notifications: {e}")
    
    async def _check_meal_reminders(self, current_utc: datetime):
        """Check if any users need meal reminders at the current UTC time."""
        try:
            meal_types = ["breakfast", "lunch", "dinner"]
            
            for meal_type in meal_types:
                user_ids = self.notification_repository.find_users_for_meal_reminder(
                    meal_type, current_utc  # Pass datetime, not minutes
                )
                
                for user_id in user_ids:
                    try:
                        result = await self.notification_service.send_meal_reminder(
                            user_id, meal_type
                        )
                        
                        if result.get("success"):
                            logger.info(f"Meal reminder sent to user {user_id} for {meal_type}")
                        else:
                            logger.warning(f"Failed to send meal reminder to user {user_id}: {result}")
                            
                    except Exception as e:
                        logger.error(f"Error sending meal reminder to user {user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error checking meal reminders: {e}")
    
    async def _check_sleep_reminders(self, current_utc: datetime):
        """Check if any users need sleep reminders at the current UTC time."""
        try:
            user_ids = self.notification_repository.find_users_for_sleep_reminder(
                current_utc  # Pass datetime, not minutes
            )
            
            for user_id in user_ids:
                try:
                    result = await self.notification_service.send_sleep_reminder(user_id)
                    
                    if result.get("success"):
                        logger.info(f"Sleep reminder sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send sleep reminder to user {user_id}: {result}")
                        
                except Exception as e:
                    logger.error(f"Error sending sleep reminder to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking sleep reminders: {e}")
    
    async def _check_water_reminders(self, current_utc: datetime):
        """Check if any users need water reminders based on their interval."""
        try:
            user_ids = self.notification_repository.find_users_for_water_reminder(current_utc)

            # Limit to avoid sending too many at once
            limited_user_ids = user_ids[:self.WATER_REMINDER_MAX_BATCH_SIZE]
            
            for user_id in limited_user_ids:
                try:
                    result = await self.notification_service.send_water_reminder(user_id)
                    
                    if result.get("success"):
                        # Update last sent timestamp
                        self.notification_repository.update_last_water_reminder(user_id, current_utc)
                        logger.info(f"Water reminder sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send water reminder to user {user_id}: {result}")
                        
                except Exception as e:
                    logger.error(f"Error sending water reminder to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking water reminders: {e}")
    
    async def send_test_notification(
        self,
        user_id: str,
        notification_type: str = "test"
    ) -> Dict[str, any]:
        """Send a test notification to a user."""
        try:
            result = await self.notification_service.send_notification(
                user_id=user_id,
                title="🧪 Test Notification",
                body="This is a test notification from the backend",
                notification_type=NotificationType.PROGRESS_NOTIFICATION,
                data={"type": "test", "timestamp": utc_now().isoformat()}
            )
            
            logger.info(f"Test notification sent to user {user_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending test notification to user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running
