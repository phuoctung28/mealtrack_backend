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
