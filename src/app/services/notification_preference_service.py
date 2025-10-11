"""
Service for managing user notification preferences.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.infra.database.models.user.profile import UserProfile
from src.domain.model.notification import NotificationPreferences

logger = logging.getLogger(__name__)


class NotificationPreferenceService:
    """Service for managing notification preferences"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """
        Get user notification preferences
        
        Args:
            user_id: User ID
            
        Returns:
            NotificationPreferences if user profile exists, None otherwise
        """
        try:
            # Get current user profile
            result = await self.session.execute(
                select(UserProfile).where(
                    UserProfile.user_id == user_id,
                    UserProfile.is_current == True
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                logger.warning(f"No current profile found for user {user_id}")
                return None
            
            # Build preferences from profile
            return NotificationPreferences(
                notifications_enabled=profile.notifications_enabled,
                push_notifications_enabled=profile.push_notifications_enabled,
                email_notifications_enabled=profile.email_notifications_enabled,
                weekly_weight_reminder_enabled=profile.weekly_weight_reminder_enabled,
                weekly_weight_reminder_day=profile.weekly_weight_reminder_day,
                weekly_weight_reminder_time=profile.weekly_weight_reminder_time
            )
            
        except Exception as e:
            logger.error(f"Error getting notification preferences for user {user_id}: {e}")
            raise
    
    async def update_preferences(
        self,
        user_id: str,
        notifications_enabled: Optional[bool] = None,
        push_notifications_enabled: Optional[bool] = None,
        email_notifications_enabled: Optional[bool] = None,
        weekly_weight_reminder_enabled: Optional[bool] = None,
        weekly_weight_reminder_day: Optional[int] = None,
        weekly_weight_reminder_time: Optional[str] = None
    ) -> NotificationPreferences:
        """
        Update user notification preferences
        
        Args:
            user_id: User ID
            notifications_enabled: Master notification toggle
            push_notifications_enabled: Push notification toggle
            email_notifications_enabled: Email notification toggle
            weekly_weight_reminder_enabled: Weekly weight reminder toggle
            weekly_weight_reminder_day: Day of week for reminder (0=Sunday, 6=Saturday)
            weekly_weight_reminder_time: Time of day for reminder (HH:mm format)
            
        Returns:
            Updated NotificationPreferences
            
        Raises:
            ValueError: If user profile not found or invalid values provided
        """
        try:
            # Get current user profile
            result = await self.session.execute(
                select(UserProfile).where(
                    UserProfile.user_id == user_id,
                    UserProfile.is_current == True
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                raise ValueError(f"No current profile found for user {user_id}")
            
            # Build update values
            update_values = {}
            
            if notifications_enabled is not None:
                update_values['notifications_enabled'] = notifications_enabled
            
            if push_notifications_enabled is not None:
                update_values['push_notifications_enabled'] = push_notifications_enabled
            
            if email_notifications_enabled is not None:
                update_values['email_notifications_enabled'] = email_notifications_enabled
            
            if weekly_weight_reminder_enabled is not None:
                update_values['weekly_weight_reminder_enabled'] = weekly_weight_reminder_enabled
            
            if weekly_weight_reminder_day is not None:
                if not (0 <= weekly_weight_reminder_day <= 6):
                    raise ValueError("Reminder day must be 0-6 (0=Sunday, 6=Saturday)")
                update_values['weekly_weight_reminder_day'] = weekly_weight_reminder_day
            
            if weekly_weight_reminder_time is not None:
                # Basic validation - more thorough validation in domain model
                if ':' not in weekly_weight_reminder_time or len(weekly_weight_reminder_time) != 5:
                    raise ValueError("Reminder time must be in HH:mm format")
                update_values['weekly_weight_reminder_time'] = weekly_weight_reminder_time
            
            # Update profile if there are changes
            if update_values:
                await self.session.execute(
                    update(UserProfile)
                    .where(
                        UserProfile.user_id == user_id,
                        UserProfile.is_current == True
                    )
                    .values(**update_values)
                )
                await self.session.commit()
                
                # Refresh profile
                await self.session.refresh(profile)
                
                logger.info(f"Updated notification preferences for user {user_id}")
            
            # Return updated preferences
            return NotificationPreferences(
                notifications_enabled=profile.notifications_enabled,
                push_notifications_enabled=profile.push_notifications_enabled,
                email_notifications_enabled=profile.email_notifications_enabled,
                weekly_weight_reminder_enabled=profile.weekly_weight_reminder_enabled,
                weekly_weight_reminder_day=profile.weekly_weight_reminder_day,
                weekly_weight_reminder_time=profile.weekly_weight_reminder_time
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating notification preferences for user {user_id}: {e}")
            await self.session.rollback()
            raise
    
    async def can_send_notification(
        self,
        user_id: str,
        delivery_method: str
    ) -> bool:
        """
        Check if notification can be sent to user
        
        Args:
            user_id: User ID
            delivery_method: 'push' or 'email'
            
        Returns:
            True if notification can be sent, False otherwise
        """
        try:
            preferences = await self.get_preferences(user_id)
            
            if not preferences:
                return False
            
            if not preferences.notifications_enabled:
                return False
            
            if delivery_method == 'push':
                return preferences.can_send_push()
            elif delivery_method == 'email':
                return preferences.can_send_email()
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking notification permission for user {user_id}: {e}")
            return False

