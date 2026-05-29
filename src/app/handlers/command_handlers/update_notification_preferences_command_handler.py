"""
Handler for updating notification preferences.
"""

import logging
from typing import Any, Dict, Optional

from src.app.commands.notification import UpdateNotificationPreferencesCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.notification import NotificationPreferences
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

logger = logging.getLogger(__name__)


@handles(UpdateNotificationPreferencesCommand)
class UpdateNotificationPreferencesCommandHandler(
    EventHandler[UpdateNotificationPreferencesCommand, Dict[str, Any]]
):
    """Handler for updating notification preferences."""

    def __init__(
        self,
        cache_service: Optional[CachePort] = None,
        precompute_service: Optional[DailyContextPrecomputeService] = None,
    ):
        self.cache_service = cache_service
        self.precompute_service = precompute_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if "precompute_service" in kwargs:
            self.precompute_service = kwargs["precompute_service"]

    async def handle(
        self, command: UpdateNotificationPreferencesCommand
    ) -> Dict[str, Any]:
        """Handle notification preferences update."""
        try:
            async with AsyncUnitOfWork() as uow:
                existing_prefs = (
                    await uow.notifications.find_notification_preferences_by_user(
                        command.user_id
                    )
                )

                if not existing_prefs:
                    existing_prefs = NotificationPreferences.create_default(
                        command.user_id
                    )
                    saved_prefs = await uow.notifications.save_notification_preferences(
                        existing_prefs
                    )
                else:
                    saved_prefs = existing_prefs

                updated_prefs = saved_prefs.update_preferences(
                    meal_reminders_enabled=command.meal_reminders_enabled,
                    daily_summary_enabled=command.daily_summary_enabled,
                    hydration_reminders_enabled=command.hydration_reminders_enabled,
                    breakfast_time_minutes=command.breakfast_time_minutes,
                    lunch_time_minutes=command.lunch_time_minutes,
                    dinner_time_minutes=command.dinner_time_minutes,
                    daily_summary_time_minutes=command.daily_summary_time_minutes,
                    language=command.language,
                )

                final_prefs = await uow.notifications.save_notification_preferences(
                    updated_prefs
                )
                await uow.commit()

                logger.info(
                    f"Notification preferences updated for user {command.user_id}"
                )
                result = {"success": True, "preferences": final_prefs.to_dict()}

        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
            raise e

        # Invalidate cache
        if self.cache_service:
            cache_key, _ = CacheKeys.notification_prefs(command.user_id)
            await self.cache_service.invalidate(cache_key)

        # Reschedule notifications with updated times (real-time update)
        if self.precompute_service:
            try:
                scheduled_count = await self.precompute_service.reschedule_user_notifications(
                    command.user_id
                )
                logger.info(
                    f"Rescheduled {scheduled_count} notifications for user {command.user_id}"
                )
            except Exception as e:
                logger.error(f"Failed to reschedule notifications: {e}")

        return result
