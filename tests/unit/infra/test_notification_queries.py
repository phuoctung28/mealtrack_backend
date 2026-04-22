"""
Unit tests for notification query builder.

Note: TestFixedWaterReminderQueries removed — fixed water reminder
functionality was removed from ReminderQueryBuilder.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock


def test_find_due_notifications_queries_pending_in_window():
    from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder
    from src.infra.database.models.notification.notification import NotificationORM

    now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
    mock_notif = MagicMock(spec=NotificationORM)
    mock_notif.status = 'pending'

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_notif]

    db = MagicMock()
    db.query.return_value = mock_query

    results = ReminderQueryBuilder.find_due_notifications(db, now)

    db.query.assert_called_once_with(NotificationORM)
    assert results == [mock_notif]


def test_find_due_notifications_includes_past_due_rows(test_session, sample_user):
    """Past-due pending rows must be returned — no lower bound on scheduled_for_utc."""
    from datetime import timedelta
    from src.infra.database.models.notification.notification import NotificationORM
    from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder
    import uuid

    now = datetime(2026, 4, 22, 8, 0, 0, tzinfo=timezone.utc)
    past_due = NotificationORM(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        notification_type="meal_reminder_breakfast",
        scheduled_date=now.date(),
        scheduled_for_utc=now - timedelta(minutes=5),  # 5 min in the past
        status="pending",
        context={"fcm_tokens": []},
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    test_session.add(past_due)
    test_session.flush()

    results = ReminderQueryBuilder.find_due_notifications(test_session, now)
    assert any(r.id == past_due.id for r in results), "Past-due pending row must be returned"
