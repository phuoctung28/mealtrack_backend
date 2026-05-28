from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder


def test_find_due_notifications_applies_limit():
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
    ReminderQueryBuilder.find_due_notifications(mock_db, now, lock_rows=False)

    mock_query.limit.assert_called_once_with(500)


def test_find_due_notifications_limit_applied_before_all():
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
    ReminderQueryBuilder.find_due_notifications(mock_db, now)

    call_order = mock_query.method_calls
    limit_idx = next(i for i, c in enumerate(call_order) if c[0] == "limit")
    all_idx = next(i for i, c in enumerate(call_order) if c[0] == "all")
    assert limit_idx < all_idx
