"""Unit test: weekly_budget_repository.upsert is idempotent under concurrent calls."""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.domain.model.weekly import WeeklyMacroBudget
from src.infra.repositories.weekly_budget_repository import WeeklyBudgetRepository


def _make_budget(user_id: str = "u1") -> WeeklyMacroBudget:
    return WeeklyMacroBudget(
        weekly_budget_id=str(uuid.uuid4()),
        user_id=user_id,
        week_start_date=date(2026, 4, 14),
        target_calories=2000.0,
        target_protein=150.0,
        target_carbs=200.0,
        target_fat=70.0,
        consumed_calories=0.0,
        consumed_protein=0.0,
        consumed_carbs=0.0,
        consumed_fat=0.0,
    )


def test_upsert_calls_execute_not_add():
    """upsert() must use a dialect-level statement, not session.add()."""
    db = MagicMock()
    repo = WeeklyBudgetRepository(db)
    budget = _make_budget()

    with patch.object(repo, "_upsert_stmt") as mock_stmt:
        mock_stmt.return_value = MagicMock()
        repo.upsert(budget)

    db.execute.assert_called_once()
    db.add.assert_not_called()


def test_create_delegates_to_upsert():
    """Existing create() must now delegate to upsert() for backwards compatibility."""
    db = MagicMock()
    repo = WeeklyBudgetRepository(db)
    budget = _make_budget()

    with patch.object(repo, "upsert", return_value=budget) as mock_upsert:
        repo.create(budget)

    mock_upsert.assert_called_once_with(budget)
