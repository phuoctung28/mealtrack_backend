import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_detects_midnight_timezone():
    from src.infra.services.scheduled_notification_service import _timezones_at_midnight
    # 2026-04-22 17:00 UTC = 2026-04-23 00:00 Asia/Ho_Chi_Minh (UTC+7)
    now = datetime(2026, 4, 22, 17, 0, 0, tzinfo=timezone.utc)
    result = _timezones_at_midnight(['Asia/Ho_Chi_Minh', 'UTC'], now)
    assert 'Asia/Ho_Chi_Minh' in result
    assert 'UTC' not in result


@pytest.mark.asyncio
async def test_send_loop_marks_notifications_sent():
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService

    mock_notif = MagicMock()
    mock_notif.notification_type = 'meal_reminder_breakfast'
    mock_notif.context = {
        'fcm_tokens': ['tok1'],
        'calorie_goal': 1800,
        'gender': 'male',
        'language_code': 'en',
    }
    mock_notif.id = 'notif-id-1'
    mock_notif.user_id = 'user-1'

    mock_redis = AsyncMock()
    mock_redis.hgetall_batch = AsyncMock(return_value=[{'calories_consumed': '0'}])
    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(return_value={'success': True, 'failed_tokens': []})

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._redis = mock_redis
    svc._firebase = mock_firebase
    svc._running = True

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_notif]
    mock_db.query.return_value.filter.return_value.update = MagicMock()

    with patch('src.infra.services.scheduled_notification_service.ReminderQueryBuilder') as mock_qb, \
         patch('src.infra.services.scheduled_notification_service.UnitOfWork') as mock_uow:
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = mock_db

        now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

    mock_firebase.send_multicast.assert_called_once()
