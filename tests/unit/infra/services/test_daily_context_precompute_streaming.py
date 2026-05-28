from unittest.mock import MagicMock, patch
from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService


def test_token_query_does_not_call_fetchall():
    """Queries 2-4 must not call fetchall() — they should iterate cursor directly."""
    service = DailyContextPrecomputeService()

    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    mock_result.fetchall = MagicMock()

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result

    mock_uow = MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow.session = mock_session

    # Query 1 returns one user so the method doesn't exit early
    pref_row = MagicMock()
    pref_row.user_id = "user-1"

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First query (pref_rows) — return one row via fetchall
            r = MagicMock()
            r.__iter__ = MagicMock(return_value=iter([pref_row]))
            r.fetchall = MagicMock(return_value=[pref_row])
            return r
        return mock_result

    mock_session.execute.side_effect = side_effect

    from datetime import date
    with patch("src.infra.services.daily_context_precompute_service.UnitOfWork", return_value=mock_uow):
        try:
            service._precompute_db_sync("UTC", date.today())
        except Exception:
            pass  # May fail due to incomplete mock — we only care about fetchall calls on queries 2-4

    # fetchall should only be called on query 1, not on queries 2-4
    assert mock_result.fetchall.call_count == 0, (
        "Queries 2-4 must not call fetchall() — iterate cursor directly"
    )
