"""
Scheduled notification service for sending push notifications at specific times.

Only one worker per process host runs the scheduler loop (see SchedulerLeaderLock).
Horizontal scaling across multiple containers still runs one scheduler per instance;
use Redis/DB leader election or a dedicated worker if exactly-once cluster-wide is required.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from src.domain.model.notification import NotificationType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.services.notification_service import NotificationService
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.services.meal_suggestion.suggestion_tdee_helpers import build_tdee_request
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import utc_now, timezone
from src.infra.database.uow import UnitOfWork
from src.infra.services.scheduler_leader_lock import SchedulerLeaderLock

logger = logging.getLogger(__name__)


class ScheduledNotificationService:
    """Service for scheduling and sending notifications at specific times.

    Leader election is per host (flock); multi-container deployments need a separate
    coordination strategy if a single cluster-wide scheduler is required.
    """

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
        self._cleanup_counter = 0  # Clean sent logs every ~60 loop ticks (~1h)
        self._leader_lock = SchedulerLeaderLock()
        self._leader_acquired = False

    async def start(self):
        """Start the scheduled notification service."""
        if self._running:
            logger.warning("Scheduled notification service is already running")
            return

        if not self._leader_lock.try_acquire():
            logger.info(
                "Scheduled notification service skipped: another worker holds the "
                "scheduler lock (see scheduler_leader_lock)"
            )
            return

        self._leader_acquired = True
        self._running = True
        logger.info("Starting scheduled notification service (scheduler leader)")
        
        # Start the main scheduling loop
        task = asyncio.create_task(self._scheduling_loop())
        self._tasks.append(task)
        
        logger.info("Scheduled notification service started")
    
    async def stop(self):
        """Stop the scheduled notification service."""
        if not self._leader_acquired:
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
        self._leader_lock.release()
        self._leader_acquired = False
        logger.info("Scheduled notification service stopped")
    
    async def _scheduling_loop(self):
        """Main scheduling loop that runs every minute."""
        while self._running:
            try:
                current_time = datetime.now(timezone.utc)
                await self._check_and_send_notifications(current_time)

                # Periodically clean old dedup logs (~every hour)
                self._cleanup_counter += 1
                if self._cleanup_counter >= 60:
                    self._cleanup_counter = 0
                    self.notification_service.cleanup_old_sent_logs()

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
                    # Get gender, remaining calories, and language for personalized messages
                    gender, remaining_cal, language = await self._get_user_context(
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
                    # Get user's daily nutrition data + gender + language
                    daily_summary = await self._get_user_daily_summary(user_id)
                    language = daily_summary.get("language", "en")

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
        """Get user's gender, remaining calories, and language for notifications.

        Returns (gender, remaining_calories, language) tuple.
        Uses shared WeeklyBudgetService for consistent values with the app API.
        """
        from src.domain.utils.timezone_utils import (
            resolve_user_timezone, user_today, get_user_monday,
        )

        with UnitOfWork() as uow:
            user = uow.users.find_by_id(user_id)
            language = getattr(user, 'language_code', 'en') if user else "en"

            profile = uow.users.get_profile(user_id)
            gender = profile.gender if profile else "male"

            # Compute adjusted daily + consumed from shared service
            calorie_goal = 2000
            calories_consumed = 0.0
            if profile:
                try:
                    tdee_result = self._tdee_service.calculate_tdee(
                        build_tdee_request(profile)
                    )
                    user_tz = resolve_user_timezone(user_id, uow)
                    today = user_today(user_tz)
                    week_start = get_user_monday(today, user_id, uow)
                    weekly_budget = uow.weekly_budgets.find_by_user_and_week(
                        user_id, week_start
                    )

                    if weekly_budget:
                        effective = WeeklyBudgetService.get_effective_adjusted_daily(
                            uow=uow, user_id=user_id,
                            week_start=week_start, target_date=today,
                            weekly_budget=weekly_budget,
                            base_daily_cal=tdee_result.macros.calories,
                            base_daily_protein=tdee_result.macros.protein,
                            base_daily_carbs=tdee_result.macros.carbs,
                            base_daily_fat=tdee_result.macros.fat,
                            bmr=tdee_result.bmr, user_timezone=user_tz,
                        )
                        calorie_goal = effective.adjusted.calories
                        # consumed_today = total - before_today (same as app API)
                        calories_consumed = (
                            effective.consumed_total["calories"]
                            - effective.consumed_before_today["calories"]
                        )
                    else:
                        calorie_goal = tdee_result.macros.calories
                except Exception as e:
                    logger.warning(
                        f"Adjusted daily target failed for {user_id}: {e}"
                    )

            remaining = max(0, int(calorie_goal - calories_consumed))
            logger.info(
                f"Notification context for {user_id}: "
                f"goal={calorie_goal:.0f}, consumed={calories_consumed:.0f}, "
                f"remaining={remaining}"
            )
            return gender, remaining, language

    async def _get_user_daily_summary(self, user_id: str) -> dict:
        """Get user's daily nutrition summary for the given date.

        Returns dict with calories_consumed, calorie_goal, meals_logged, gender.
        Uses shared WeeklyBudgetService for consistent values with the app API.
        """
        from src.infra.repositories.meal_repository import MealRepository
        from src.domain.utils.timezone_utils import (
            resolve_user_timezone, user_today, get_user_monday,
        )

        with UnitOfWork() as uow:
            user = uow.users.find_by_id(user_id)
            language = getattr(user, 'language_code', 'en') if user else "en"

            profile = uow.users.get_profile(user_id)
            gender = profile.gender if profile else "male"

            user_tz = resolve_user_timezone(user_id, uow)
            local_date = user_today(user_tz)

            # meals_logged count still needs find_by_date (for count only)
            meal_repo = MealRepository(uow.session)
            meals = meal_repo.find_by_date(
                local_date, user_id=user_id, user_timezone=user_tz
            )
            meals_logged = len(meals)

            # Use shared service for goal + consumed (consistent with app API)
            calorie_goal = 2000
            calories_consumed = 0.0
            if profile:
                try:
                    tdee_result = self._tdee_service.calculate_tdee(
                        build_tdee_request(profile)
                    )
                    today = local_date
                    week_start = get_user_monday(today, user_id, uow)
                    weekly_budget = uow.weekly_budgets.find_by_user_and_week(
                        user_id, week_start
                    )

                    if weekly_budget:
                        effective = WeeklyBudgetService.get_effective_adjusted_daily(
                            uow=uow, user_id=user_id,
                            week_start=week_start, target_date=today,
                            weekly_budget=weekly_budget,
                            base_daily_cal=tdee_result.macros.calories,
                            base_daily_protein=tdee_result.macros.protein,
                            base_daily_carbs=tdee_result.macros.carbs,
                            base_daily_fat=tdee_result.macros.fat,
                            bmr=tdee_result.bmr, user_timezone=user_tz,
                        )
                        calorie_goal = effective.adjusted.calories
                        calories_consumed = (
                            effective.consumed_total["calories"]
                            - effective.consumed_before_today["calories"]
                        )
                    else:
                        calorie_goal = tdee_result.macros.calories
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
                "language": language,
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
