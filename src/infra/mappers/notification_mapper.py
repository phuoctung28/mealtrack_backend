"""Notification ORM <-> domain mapping functions."""

from src.domain.model.notification import (
    UserFcmToken,
    NotificationPreferences,
    DeviceType,
)
from src.infra.database.models.notification.user_fcm_token import UserFcmTokenORM
from src.infra.database.models.notification.notification_preferences import (
    NotificationPreferencesORM,
)

# ---------------------------------------------------------------------------
# UserFcmToken
# ---------------------------------------------------------------------------


def fcm_token_orm_to_domain(orm: UserFcmTokenORM) -> UserFcmToken:
    device_type = DeviceType.IOS if orm.device_type == "ios" else DeviceType.ANDROID

    return UserFcmToken(
        token_id=orm.id,
        user_id=orm.user_id,
        fcm_token=orm.fcm_token,
        device_type=device_type,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------------------------------------------------------------------------
# NotificationPreferences
# ---------------------------------------------------------------------------


def notification_prefs_orm_to_domain(
    orm: NotificationPreferencesORM,
) -> NotificationPreferences:
    return NotificationPreferences(
        preferences_id=orm.id,
        user_id=orm.user_id,
        meal_reminders_enabled=orm.meal_reminders_enabled,
        daily_summary_enabled=orm.daily_summary_enabled,
        breakfast_time_minutes=orm.breakfast_time_minutes,
        lunch_time_minutes=orm.lunch_time_minutes,
        dinner_time_minutes=orm.dinner_time_minutes,
        daily_summary_time_minutes=orm.daily_summary_time_minutes,
        language=orm.language,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
