from typing import List, Optional
from datetime import datetime

from src.domain.model.notification import UserFcmToken, NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort


class FakeNotificationRepository(NotificationRepositoryPort):
    def __init__(self):
        self.fcm_tokens = {}  # token_string -> UserFcmToken
        self.preferences = {}  # user_id -> NotificationPreferences

    # FCM Token operations
    async def save_fcm_token(self, token: UserFcmToken) -> UserFcmToken:
        self.fcm_tokens[token.token] = token
        return token

    async def find_fcm_token_by_token(self, fcm_token: str) -> Optional[UserFcmToken]:
        return self.fcm_tokens.get(fcm_token)

    async def find_active_fcm_tokens_by_user(self, user_id: str) -> List[UserFcmToken]:
        return [
            t for t in self.fcm_tokens.values() if t.user_id == user_id and t.is_active
        ]

    async def deactivate_fcm_token(self, fcm_token: str) -> bool:
        if fcm_token in self.fcm_tokens:
            self.fcm_tokens[fcm_token].is_active = False
            return True
        return False

    async def delete_fcm_token(self, fcm_token: str) -> bool:
        if fcm_token in self.fcm_tokens:
            del self.fcm_tokens[fcm_token]
            return True
        return False

    # Notification Preferences operations
    async def save_notification_preferences(
        self, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        self.preferences[preferences.user_id] = preferences
        return preferences

    async def find_notification_preferences_by_user(
        self, user_id: str
    ) -> Optional[NotificationPreferences]:
        return self.preferences.get(user_id)

    async def update_notification_preferences(
        self, user_id: str, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        self.preferences[user_id] = preferences
        return preferences

    async def delete_notification_preferences(self, user_id: str) -> bool:
        if user_id in self.preferences:
            del self.preferences[user_id]
            return True
        return False

    # Utility operations (Stubbed)
    async def find_users_for_meal_reminder(
        self, meal_type: str, current_utc: datetime
    ) -> List[str]:
        return []

    async def find_users_for_sleep_reminder(self, current_utc: datetime) -> List[str]:
        return []

    async def find_users_for_fixed_water_reminder(
        self, current_utc: datetime
    ) -> List[str]:
        return []

    async def find_users_for_daily_summary(self, current_utc: datetime) -> List[str]:
        return []

    async def update_last_water_reminder(self, user_id: str, sent_at: datetime) -> bool:
        if user_id in self.preferences:
            self.preferences[user_id].last_water_reminder_at = sent_at
            return True
        return False
