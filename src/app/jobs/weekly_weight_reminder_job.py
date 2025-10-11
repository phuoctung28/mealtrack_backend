"""
Background job to send weekly weight reminders.
"""
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from src.domain.model.notification import Notification
from src.app.services.notification_preference_service import NotificationPreferenceService
from src.app.services.notification_dispatch_service import NotificationDispatchService
from src.app.services.push_notification_service import PushNotificationService
from src.app.services.email_notification_service import EmailNotificationService
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)

logger = logging.getLogger(__name__)


class WeeklyWeightReminderJob:
    """Background job to send weekly weight reminders"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def run(self):
        """Execute the reminder job"""
        logger.info("Starting weekly weight reminder job")
        
        try:
            # Get current day and time
            now = datetime.now()
            # Convert Python weekday (0=Monday) to our format (0=Sunday)
            current_day = (now.weekday() + 1) % 7
            current_time = now.strftime("%H:%M")
            
            # Find users with reminders scheduled for current day/time
            users = await self._find_users_to_remind(current_day, current_time)
            
            logger.info(f"Found {len(users)} users to remind at {current_time} on day {current_day}")
            
            if not users:
                logger.info("No users to remind at this time")
                return
            
            # Initialize services
            device_repo = DeviceTokenRepository(self.session)
            notif_repo = NotificationLogRepository(self.session)
            preference_service = NotificationPreferenceService(self.session)
            push_service = PushNotificationService(device_repo, notif_repo)
            email_service = EmailNotificationService(notif_repo)
            dispatch_service = NotificationDispatchService(
                preference_service,
                push_service,
                email_service
            )
            
            successful = 0
            failed = 0
            
            for user in users:
                try:
                    # Calculate days since last weight update
                    days_since = await self._calculate_days_since_last_weight(user.id)
                    
                    # Create notification
                    notification = Notification(
                        user_id=user.id,
                        notification_type='weight_reminder',
                        delivery_method='push',
                        title="Time to update your weight! ⚖️",
                        body=f"It's been {days_since} days since your last update. Track your progress to stay on target.",
                        data={
                            'action': 'weight_update',
                            'days_since': days_since
                        }
                    )
                    
                    # Dispatch notification
                    results = await dispatch_service.dispatch_notification(
                        user_id=user.id,
                        notification=notification,
                        user_email=user.email,
                        user_name=user.display_name or user.username
                    )
                    
                    if results['push'] or results['email']:
                        successful += 1
                        logger.debug(f"Sent reminder to user {user.id}")
                    else:
                        failed += 1
                        logger.warning(f"No notifications sent to user {user.id}")
                    
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to send reminder to user {user.id}: {e}")
            
            logger.info(
                f"Weekly weight reminder job completed: "
                f"{successful} successful, {failed} failed out of {len(users)} users"
            )
            
        except Exception as e:
            logger.error(f"Error in weekly weight reminder job: {e}", exc_info=True)
    
    async def _find_users_to_remind(
        self,
        day: int,
        time: str
    ) -> List[User]:
        """
        Find users who should receive reminder at this day/time
        
        Args:
            day: Day of week (0=Sunday, 6=Saturday)
            time: Time in HH:mm format
            
        Returns:
            List of users to remind
        """
        try:
            # Calculate time window (±5 minutes)
            time_start = self._subtract_minutes(time, 5)
            time_end = self._add_minutes(time, 5)
            
            # Query users with matching reminder schedule
            # Join User with current UserProfile
            query = (
                select(User)
                .join(UserProfile, UserProfile.user_id == User.id)
                .where(
                    and_(
                        UserProfile.is_current == True,
                        UserProfile.notifications_enabled == True,
                        UserProfile.weekly_weight_reminder_enabled == True,
                        UserProfile.weekly_weight_reminder_day == day,
                        UserProfile.weekly_weight_reminder_time >= time_start,
                        UserProfile.weekly_weight_reminder_time <= time_end
                    )
                )
            )
            
            result = await self.session.execute(query)
            users = list(result.scalars().all())
            
            return users
            
        except Exception as e:
            logger.error(f"Error finding users to remind: {e}")
            return []
    
    async def _calculate_days_since_last_weight(self, user_id: str) -> int:
        """
        Calculate days since last weight update
        
        Args:
            user_id: User ID
            
        Returns:
            Number of days since last weight update (7 if no previous update found)
        """
        try:
            # Get most recent profile for user
            query = (
                select(UserProfile)
                .where(UserProfile.user_id == user_id)
                .order_by(UserProfile.created_at.desc())
                .limit(1)
            )
            
            result = await self.session.execute(query)
            latest_profile = result.scalar_one_or_none()
            
            if not latest_profile:
                return 7  # Default to 7 days if no profile found
            
            # Calculate days since profile creation (weight update)
            days_since = (datetime.now() - latest_profile.created_at).days
            
            # If more than 7 days, just return 7+ to avoid very large numbers
            return min(days_since, 30)
            
        except Exception as e:
            logger.error(f"Error calculating days since last weight for user {user_id}: {e}")
            return 7  # Default to 7 days on error
    
    @staticmethod
    def _subtract_minutes(time_str: str, minutes: int) -> str:
        """
        Subtract minutes from HH:mm time string
        
        Args:
            time_str: Time in HH:mm format
            minutes: Minutes to subtract
            
        Returns:
            New time in HH:mm format
        """
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            new_time = time_obj - timedelta(minutes=minutes)
            return new_time.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Error subtracting minutes from {time_str}: {e}")
            return time_str
    
    @staticmethod
    def _add_minutes(time_str: str, minutes: int) -> str:
        """
        Add minutes to HH:mm time string
        
        Args:
            time_str: Time in HH:mm format
            minutes: Minutes to add
            
        Returns:
            New time in HH:mm format
        """
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            new_time = time_obj + timedelta(minutes=minutes)
            return new_time.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Error adding minutes to {time_str}: {e}")
            return time_str

