"""
Handler for updating notification preferences.
"""
import logging
from typing import Any, Dict

from src.app.commands.notification import UpdateNotificationPreferencesCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.notification import NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


@handles(UpdateNotificationPreferencesCommand)
class UpdateNotificationPreferencesCommandHandler(EventHandler[UpdateNotificationPreferencesCommand, Dict[str, Any]]):
    """Handler for updating notification preferences."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort = None):
        self.notification_repository = notification_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.notification_repository = kwargs.get('notification_repository', self.notification_repository)
    
    async def handle(self, command: UpdateNotificationPreferencesCommand) -> Dict[str, Any]:
        """Handle notification preferences update."""
        if not self.notification_repository:
            raise RuntimeError("Notification repository not configured")
        
        try:
            # Get existing preferences or create default
            existing_prefs = self.notification_repository.find_notification_preferences_by_user(command.user_id)
            
            if not existing_prefs:
                # Create default preferences
                existing_prefs = NotificationPreferences.create_default(command.user_id)
                saved_prefs = self.notification_repository.save_notification_preferences(existing_prefs)
            else:
                saved_prefs = existing_prefs
            
            # Update preferences with new values
            updated_prefs = saved_prefs.update_preferences(
                meal_reminders_enabled=command.meal_reminders_enabled,
                water_reminders_enabled=command.water_reminders_enabled,
                sleep_reminders_enabled=command.sleep_reminders_enabled,
                progress_notifications_enabled=command.progress_notifications_enabled,
                reengagement_notifications_enabled=command.reengagement_notifications_enabled,
                breakfast_time_minutes=command.breakfast_time_minutes,
                lunch_time_minutes=command.lunch_time_minutes,
                dinner_time_minutes=command.dinner_time_minutes,
                water_reminder_interval_hours=command.water_reminder_interval_hours,
                sleep_reminder_time_minutes=command.sleep_reminder_time_minutes,
            )
            
            # Save updated preferences
            final_prefs = self.notification_repository.save_notification_preferences(updated_prefs)
            
            logger.info(f"Notification preferences updated for user {command.user_id}")
            
            return {
                "success": True,
                "preferences": final_prefs.to_dict()
            }
        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
            raise e