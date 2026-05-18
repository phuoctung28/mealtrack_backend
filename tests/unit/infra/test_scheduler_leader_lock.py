from unittest.mock import MagicMock, patch


def test_db_lock_rejects_second_scheduler_leader():
    from src.infra.services.scheduler_leader_lock import SchedulerLeaderLock

    conn = MagicMock()
    conn.execute.return_value.scalar.return_value = False
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.connect.return_value = conn

    lock = SchedulerLeaderLock()
    with patch("src.infra.database.config.engine", engine):
        assert lock._try_acquire_db_lock() is False

    conn.close.assert_called_once()


def test_release_unlocks_postgres_advisory_lock():
    from src.infra.services.scheduler_leader_lock import SchedulerLeaderLock

    conn = MagicMock()
    lock = SchedulerLeaderLock()
    lock._db_conn = conn

    lock.release()

    conn.execute.assert_called_once()
    conn.close.assert_called_once()
    assert lock._db_conn is None
