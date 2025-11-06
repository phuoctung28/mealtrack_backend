from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.model.notification import UserFcmToken, NotificationPreferences


class NotificationRepositoryPort(ABC):
    """Port interface for notification persistence operations."""
    
    # FCM Token operations
    @abstractmethod
    def save_fcm_token(self, token: UserFcmToken) -> UserFcmToken:
        """
        Persists an FCM token.
        
        Args:
            token: The FCM token to be saved
            
        Returns:
            The saved FCM token with any generated IDs
        """
        pass
    
    @abstractmethod
    def find_fcm_token_by_token(self, fcm_token: str) -> Optional[UserFcmToken]:
        """
        Finds an FCM token by the token string.
        
        Args:
            fcm_token: The FCM token string to find
            
        Returns:
            The FCM token if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_active_fcm_tokens_by_user(self, user_id: str) -> List[UserFcmToken]:
        """
        Finds all active FCM tokens for a user.
        
        Args:
            user_id: The user ID to find tokens for
            
        Returns:
            List of active FCM tokens for the user
        """
        pass
    
    @abstractmethod
    def deactivate_fcm_token(self, fcm_token: str) -> bool:
        """
        Deactivates an FCM token.
        
        Args:
            fcm_token: The FCM token string to deactivate
            
        Returns:
            True if token was found and deactivated, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_fcm_token(self, fcm_token: str) -> bool:
        """
        Deletes an FCM token.
        
        Args:
            fcm_token: The FCM token string to delete
            
        Returns:
            True if token was found and deleted, False otherwise
        """
        pass
    
    # Notification Preferences operations
    @abstractmethod
    def save_notification_preferences(self, preferences: NotificationPreferences) -> NotificationPreferences:
        """
        Persists notification preferences.
        
        Args:
            preferences: The notification preferences to be saved
            
        Returns:
            The saved notification preferences with any generated IDs
        """
        pass
    
    @abstractmethod
    def find_notification_preferences_by_user(self, user_id: str) -> Optional[NotificationPreferences]:
        """
        Finds notification preferences by user ID.
        
        Args:
            user_id: The user ID to find preferences for
            
        Returns:
            The notification preferences if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_notification_preferences(self, user_id: str, preferences: NotificationPreferences) -> NotificationPreferences:
        """
        Updates notification preferences for a user.
        
        Args:
            user_id: The user ID to update preferences for
            preferences: The updated notification preferences
            
        Returns:
            The updated notification preferences
        """
        pass
    
    @abstractmethod
    def delete_notification_preferences(self, user_id: str) -> bool:
        """
        Deletes notification preferences for a user.
        
        Args:
            user_id: The user ID to delete preferences for
            
        Returns:
            True if preferences were found and deleted, False otherwise
        """
        pass
    
    # Utility operations
    @abstractmethod
    def find_users_for_meal_reminder(self, meal_type: str, time_minutes: int) -> List[str]:
        """
        Finds user IDs who should receive meal reminders at a specific time.
        
        Args:
            meal_type: The meal type (breakfast, lunch, dinner)
            time_minutes: The time in minutes from midnight
            
        Returns:
            List of user IDs who should receive the reminder
        """
        pass
    
    @abstractmethod
    def find_users_for_sleep_reminder(self, time_minutes: int) -> List[str]:
        """
        Finds user IDs who should receive sleep reminders at a specific time.
        
        Args:
            time_minutes: The time in minutes from midnight
            
        Returns:
            List of user IDs who should receive the reminder
        """
        pass
    
    @abstractmethod
    def find_users_for_water_reminder(self) -> List[str]:
        """
        Finds user IDs who should receive water reminders.
        Note: This is a simplified version. In production, you'd need to track
        last water reminder sent time for each user.
        
        Returns:
            List of user IDs who should receive water reminders
        """
        pass
