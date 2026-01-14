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

            # Check daily summary notifications
            await self._check_daily_summary(current_time)

        except Exception as e:
            logger.error(f"Error checking notifications: {e}")
    
    async def _check_meal_reminders(self, current_utc: datetime):
        """Check if any users need lunch reminders at the current UTC time (12:00 PM)."""
        try:
            # Only check lunch reminder (breakfast/dinner removed)
            meal_type = "lunch"
            user_ids = self.notification_repository.find_users_for_meal_reminder(
                meal_type, current_utc
            )

            for user_id in user_ids:
                try:
                    result = await self.notification_service.send_meal_reminder(
                        user_id, meal_type
                    )

                    if result.get("success"):
                        logger.info(f"Lunch reminder sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send lunch reminder to user {user_id}: {result}")

                except Exception as e:
                    logger.error(f"Error sending lunch reminder to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking lunch reminders: {e}")
    
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
        """Check if any users need water reminders at their fixed time (default 4:00 PM)."""
        try:
            user_ids = self.notification_repository.find_users_for_fixed_water_reminder(current_utc)

            for user_id in user_ids:
                try:
                    result = await self.notification_service.send_water_reminder(user_id)

                    if result.get("success"):
                        logger.info(f"Fixed-time water reminder sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send water reminder to user {user_id}: {result}")

                except Exception as e:
                    logger.error(f"Error sending water reminder to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking water reminders: {e}")

    async def _check_daily_summary(self, current_utc: datetime):
        """Check if any users need daily summary at 9PM local time."""
        try:
            user_ids = self.notification_repository.find_users_for_daily_summary(current_utc)

            for user_id in user_ids:
                try:
                    # Get user's daily nutrition data
                    today = current_utc.date()
                    daily_summary = await self._get_user_daily_summary(user_id, today)

                    result = await self.notification_service.send_daily_summary(
                        user_id=user_id,
                        calories_consumed=daily_summary["calories_consumed"],
                        calorie_goal=daily_summary["calorie_goal"],
                        meals_logged=daily_summary["meals_logged"]
                    )

                    if result.get("success"):
                        logger.info(f"Daily summary sent to user {user_id}")
                    else:
                        logger.warning(f"Failed to send daily summary: {result}")

                except Exception as e:
                    logger.error(f"Error sending daily summary to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking daily summary: {e}")

    async def _get_user_daily_summary(self, user_id: str, date) -> dict:
        """Get user's daily nutrition summary for the given date.

        Returns dict with:
        - calories_consumed: total calories for the day
        - calorie_goal: user's target calorie intake (TDEE-based)
        - meals_logged: count of meals logged
        """
        # Get meals for the day (synchronous call)
        from src.infra.database.config import SessionLocal
        from src.infra.repositories.meal_repository import MealRepository

        db = SessionLocal()
        try:
            meal_repo = MealRepository(db)
            meals = meal_repo.find_by_date(date, user_id=user_id)

            # Count meals
            meals_logged = len(meals)

            # Calculate total calories consumed from all meals
            calories_consumed = 0
            for meal in meals:
                if meal.nutrition and hasattr(meal.nutrition, 'calories'):
                    calories_consumed += meal.nutrition.calories

            # Get user profile to calculate calorie goal
            from src.infra.repositories.user_repository import UserRepository
            user_repo = UserRepository(db)
            profile = user_repo.get_current_user_profile(user_id)

            # Calculate TDEE based on profile (Harris-Benedict formula)
            calorie_goal = 2000  # Default
            if profile:
                calorie_goal = self._calculate_tdee(
                    age=profile.age,
                    gender=profile.gender,
                    height_cm=profile.height_cm,
                    weight_kg=profile.weight_kg,
                    activity_level=profile.activity_level,
                    fitness_goal=profile.fitness_goal,
                )

            return {
                "calories_consumed": calories_consumed,
                "calorie_goal": calorie_goal,
                "meals_logged": meals_logged,
            }
        finally:
            db.close()

    def _calculate_tdee(self, age: int, gender: str, height_cm: float, weight_kg: float,
                        activity_level: str, fitness_goal: str) -> float:
        """Calculate Total Daily Energy Expenditure using Harris-Benedict formula with activity multiplier.

        Args:
            age: Age in years
            gender: 'male', 'female', 'other'
            height_cm: Height in centimeters
            weight_kg: Weight in kilograms
            activity_level: 'sedentary', 'light', 'moderate', 'active', 'extra'
            fitness_goal: 'maintenance', 'cutting', 'bulking'

        Returns:
            Estimated daily calorie goal
        """
        # Harris-Benedict BMR formula
        if gender == "male":
            bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
        elif gender == "female":
            bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
        else:
            # Average for other
            male_bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
            female_bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
            bmr = (male_bmr + female_bmr) / 2

        # Activity level multipliers
        activity_multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "extra": 1.9,
        }
        activity_multiplier = activity_multipliers.get(activity_level, 1.55)

        # Calculate TDEE
        tdee = bmr * activity_multiplier

        # Adjust for fitness goal
        if fitness_goal == "cutting":
            tdee *= 0.85  # 15% deficit
        elif fitness_goal == "bulking":
            tdee *= 1.10  # 10% surplus

        return tdee

    async def send_test_notification(
        self,
        user_id: str,
        notification_type: str = "test"
    ) -> Dict[str, Any]:
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
