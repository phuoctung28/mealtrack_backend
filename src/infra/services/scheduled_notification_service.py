"""
Scheduled notification service for sending push notifications at specific times.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from src.domain.model.notification import NotificationType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.services.notification_service import NotificationService
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.services.meal_suggestion.suggestion_tdee_helpers import get_adjusted_daily_target
from src.domain.utils.timezone_utils import utc_now, timezone
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


class ScheduledNotificationService:
    """Service for scheduling and sending notifications at specific times."""

    # Scheduling constants
    SCHEDULING_LOOP_INTERVAL_SECONDS = 60
    SCHEDULING_LOOP_ERROR_RETRY_SECONDS = 30

    def __init__(
        self,
        notification_repository: NotificationRepositoryPort,
        notification_service: NotificationService
    ):
        self.notification_repository = notification_repository
        self.notification_service = notification_service
        self._tdee_service = TdeeCalculationService()
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
            # Check meal reminders for all 3 meal types
            for meal_type in ("breakfast", "lunch", "dinner"):
                await self._check_meal_reminders(current_time, meal_type)

            # Check daily summary notifications
            await self._check_daily_summary(current_time)

        except Exception as e:
            logger.error(f"Error checking notifications: {e}")
    
    async def _check_meal_reminders(self, current_utc: datetime, meal_type: str):
        """Check if any users need meal reminders for the given meal type at current UTC time."""
        try:
            user_ids = self.notification_repository.find_users_for_meal_reminder(
                meal_type, current_utc
            )

            for user_id in user_ids:
                try:
                    # Look up user's preferred notification language
                    prefs = self.notification_repository.find_notification_preferences_by_user(user_id)
                    language = prefs.language if prefs else "en"

                    # Get gender + remaining calories for personalized messages
                    gender, remaining_cal = await self._get_user_context(
                        user_id
                    )

                    result = await self.notification_service.send_meal_reminder(
                        user_id, meal_type,
                        language=language,
                        gender=gender,
                        remaining_calories=remaining_cal,
                    )

                    if result.get("success"):
                        logger.info(f"{meal_type.capitalize()} reminder sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send {meal_type} reminder to user {user_id}: {result}")

                except Exception as e:
                    logger.error(f"Error sending {meal_type} reminder to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking {meal_type} reminders: {e}")
    
    async def _check_daily_summary(self, current_utc: datetime):
        """Check if any users need daily summary at 9PM local time."""
        try:
            user_ids = self.notification_repository.find_users_for_daily_summary(current_utc)

            for user_id in user_ids:
                try:
                    # Look up user's preferred notification language
                    prefs = self.notification_repository.find_notification_preferences_by_user(user_id)
                    language = prefs.language if prefs else "en"

                    # Get user's daily nutrition data + gender
                    daily_summary = await self._get_user_daily_summary(user_id)

                    result = await self.notification_service.send_daily_summary(
                        user_id=user_id,
                        calories_consumed=daily_summary["calories_consumed"],
                        calorie_goal=daily_summary["calorie_goal"],
                        meals_logged=daily_summary["meals_logged"],
                        language=language,
                        gender=daily_summary["gender"],
                    )

                    if result.get("success"):
                        logger.info(f"Daily summary sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send daily summary: {result}")

                except Exception as e:
                    logger.error(f"Error sending daily summary to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking daily summary: {e}")

    async def _get_user_context(self, user_id: str) -> tuple:
        """Get user's gender and remaining calories for personalized notifications.

        Returns (gender, remaining_calories) tuple.
        Uses single UoW for all DB ops and user's local date for meal lookup.
        """
        from src.infra.repositories.meal_repository import MealRepository
        from src.domain.utils.timezone_utils import user_today

        with UnitOfWork() as uow:
            profile = uow.users.get_profile(user_id)
            gender = profile.gender if profile else "male"

            # Resolve user timezone and derive local date
            user_tz = uow.users.get_user_timezone(user_id) or "UTC"
            local_date = user_today(user_tz)

            # Query meals using user's local date (not UTC date)
            meal_repo = MealRepository(uow.session)
            meals = meal_repo.find_by_date(
                local_date, user_id=user_id, user_timezone=user_tz
            )

            calories_consumed = sum(
                meal.nutrition.calories
                for meal in meals
                if meal.nutrition and hasattr(meal.nutrition, 'calories')
            )

            # Get adjusted daily target (falls back to raw TDEE if no budget)
            calorie_goal = 2000
            if profile:
                try:
                    calorie_goal = await get_adjusted_daily_target(
                        self._tdee_service, user_id, profile, uow=uow
                    )
                except Exception as e:
                    logger.warning(
                        f"Adjusted daily target failed for {user_id}: {e}"
                    )

            remaining = max(0, int(calorie_goal - calories_consumed))
            logger.info(
                f"Notification context for {user_id}: "
                f"goal={calorie_goal:.0f}, consumed={calories_consumed:.0f}, "
                f"remaining={remaining}, tz={user_tz}, date={local_date}"
            )
            return gender, remaining

    async def _get_user_daily_summary(self, user_id: str) -> dict:
        """Get user's daily nutrition summary for the given date.

        Returns dict with calories_consumed, calorie_goal, meals_logged, gender.
        Uses single UoW for all DB ops and user's local date for meal lookup.
        """
        from src.infra.repositories.meal_repository import MealRepository
        from src.domain.utils.timezone_utils import user_today

        with UnitOfWork() as uow:
            # Resolve user timezone and derive local date
            user_tz = uow.users.get_user_timezone(user_id) or "UTC"
            local_date = user_today(user_tz)

            meal_repo = MealRepository(uow.session)
            meals = meal_repo.find_by_date(
                local_date, user_id=user_id, user_timezone=user_tz
            )

            meals_logged = len(meals)
            calories_consumed = sum(
                meal.nutrition.calories
                for meal in meals
                if meal.nutrition and hasattr(meal.nutrition, 'calories')
            )

            profile = uow.users.get_profile(user_id)
            gender = profile.gender if profile else "male"

            calorie_goal = 2000
            if profile:
                try:
                    calorie_goal = await get_adjusted_daily_target(
                        self._tdee_service, user_id, profile, uow=uow
                    )
                except Exception as e:
                    logger.warning(
                        f"Adjusted daily target failed for {user_id}: {e}"
                    )

            logger.info(
                f"Daily summary for {user_id}: "
                f"goal={calorie_goal:.0f}, consumed={calories_consumed:.0f}, "
                f"meals={meals_logged}, tz={user_tz}, date={local_date}"
            )
            return {
                "calories_consumed": calories_consumed,
                "calorie_goal": calorie_goal,
                "meals_logged": meals_logged,
                "gender": gender,
            }

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
                notification_type=NotificationType.DAILY_SUMMARY,
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
