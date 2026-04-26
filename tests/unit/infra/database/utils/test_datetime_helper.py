import pytest
from unittest.mock import MagicMock
from sqlalchemy import func

from src.infra.database.utils.datetime_helper import local_date_expr


def test_local_date_expr_returns_func_date_for_utc_timezone():
    mock_session = MagicMock()
    mock_col = MagicMock()

    result = local_date_expr(mock_session, mock_col, "UTC")

    assert result is not None


def test_local_date_expr_returns_func_date_for_none_timezone():
    mock_session = MagicMock()
    mock_col = MagicMock()

    result = local_date_expr(mock_session, mock_col, None)

    assert result is not None


def test_local_date_expr_postgresql_uses_timezone_function():
    mock_session = MagicMock()
    mock_session.bind.dialect.name = "postgresql"
    mock_col = MagicMock()

    result = local_date_expr(mock_session, mock_col, "America/New_York")

    assert result is not None


def test_local_date_expr_sqlite_falls_back_to_func_date():
    mock_session = MagicMock()
    mock_session.bind.dialect.name = "sqlite"
    mock_col = MagicMock()

    result = local_date_expr(mock_session, mock_col, "America/New_York")

    assert result is not None


def test_local_date_expr_no_bind_falls_back_to_func_date():
    mock_session = MagicMock()
    mock_session.bind = None
    mock_col = MagicMock()

    result = local_date_expr(mock_session, mock_col, "America/New_York")

    assert result is not None
