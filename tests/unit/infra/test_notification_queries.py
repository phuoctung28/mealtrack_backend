"""
Unit tests for notification query builder.

Note: TestFixedWaterReminderQueries removed — fixed water reminder
functionality was removed from ReminderQueryBuilder.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock


def test_find_due_notifications_queries_pending_due_rows():
    from src.infra.repositories.notification.reminder_query_builder import (
        ReminderQueryBuilder,
    )
    from src.infra.database.models.notification.notification import NotificationORM

    now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
    mock_notif = MagicMock(spec=NotificationORM)
    mock_notif.status = "pending"

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [mock_notif]

    db = MagicMock()
    db.query.return_value = mock_query

    results = ReminderQueryBuilder.find_due_notifications(db, now)

    db.query.assert_called_once_with(NotificationORM)
    assert results == [mock_notif]


def test_find_due_notifications_can_lock_rows_for_scheduler_claims():
    from src.infra.repositories.notification.reminder_query_builder import (
        ReminderQueryBuilder,
    )
    from src.infra.database.models.notification.notification import NotificationORM

    now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
    mock_notif = MagicMock(spec=NotificationORM)

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.with_for_update.return_value = mock_query
    mock_query.all.return_value = [mock_notif]

    db = MagicMock()
    db.query.return_value = mock_query

    results = ReminderQueryBuilder.find_due_notifications(db, now, lock_rows=True)

    mock_query.with_for_update.assert_called_once_with(skip_locked=True)
    assert results == [mock_notif]


def test_find_due_notifications_includes_past_due_rows(test_session, sample_user):
    """Past-due pending rows must be returned — no lower bound on scheduled_for_utc."""
    from datetime import timedelta
    from src.infra.database.models.notification.notification import NotificationORM
    from src.infra.repositories.notification.reminder_query_builder import (
        ReminderQueryBuilder,
    )
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
    assert any(
        r.id == past_due.id for r in results
    ), "Past-due pending row must be returned"


def test_find_due_notifications_excludes_future_rows(test_session, sample_user):
    """Future rows must not be returned, even if they are within the next minute."""
    from datetime import timedelta
    from src.infra.database.models.notification.notification import NotificationORM
    from src.infra.repositories.notification.reminder_query_builder import (
        ReminderQueryBuilder,
    )
    import uuid

    now = datetime(2026, 4, 22, 8, 0, 0, tzinfo=timezone.utc)
    future = NotificationORM(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        notification_type="meal_reminder_lunch",
        scheduled_date=now.date(),
        scheduled_for_utc=now + timedelta(seconds=30),
        status="pending",
        context={"fcm_tokens": []},
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    test_session.add(future)
    test_session.flush()

    results = ReminderQueryBuilder.find_due_notifications(test_session, now)

    assert all(r.id != future.id for r in results)


def test_find_due_notifications_reclaims_stale_processing_rows(
    test_session, sample_user
):
    from datetime import timedelta
    import uuid

    from src.infra.database.models.notification.notification import NotificationORM
    from src.infra.repositories.notification.reminder_query_builder import (
        ReminderQueryBuilder,
    )

    now = datetime(2026, 4, 22, 8, 30, 0, tzinfo=timezone.utc)
    stale = NotificationORM(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        notification_type="meal_reminder_lunch",
        scheduled_date=now.date(),
        scheduled_for_utc=now - timedelta(minutes=15),
        status="processing",
        context={"fcm_tokens": []},
        created_at=now - timedelta(minutes=20),
        expires_at=now + timedelta(days=7),
    )
    fresh = NotificationORM(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        notification_type="meal_reminder_dinner",
        scheduled_date=now.date(),
        scheduled_for_utc=now - timedelta(minutes=2),
        status="processing",
        context={"fcm_tokens": []},
        created_at=now - timedelta(minutes=20),
        expires_at=now + timedelta(days=7),
    )
    test_session.add_all([stale, fresh])
    test_session.flush()

    results = ReminderQueryBuilder.find_due_notifications(
        test_session, now, lock_rows=True
    )

    assert any(r.id == stale.id for r in results)
    assert all(r.id != fresh.id for r in results)
