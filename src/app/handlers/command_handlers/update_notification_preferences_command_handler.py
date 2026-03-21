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
            existing_prefs = self.notification_repository.find_notification_preferences_by_user(command.user_id)

            if not existing_prefs:
                existing_prefs = NotificationPreferences.create_default(command.user_id)
                saved_prefs = self.notification_repository.save_notification_preferences(existing_prefs)
            else:
                saved_prefs = existing_prefs

            updated_prefs = saved_prefs.update_preferences(
                meal_reminders_enabled=command.meal_reminders_enabled,
                daily_summary_enabled=command.daily_summary_enabled,
                breakfast_time_minutes=command.breakfast_time_minutes,
                lunch_time_minutes=command.lunch_time_minutes,
                dinner_time_minutes=command.dinner_time_minutes,
                daily_summary_time_minutes=command.daily_summary_time_minutes,
            )

            final_prefs = self.notification_repository.save_notification_preferences(updated_prefs)

            logger.info(f"Notification preferences updated for user {command.user_id}")

            return {
                "success": True,
                "preferences": final_prefs.to_dict()
            }
        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
            raise e
