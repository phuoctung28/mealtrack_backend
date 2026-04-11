"""Unit tests for MealTranslationRepository with mocked DB session."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.model.meal.meal_translation_domain_models import (
    FoodItemTranslation,
    MealTranslation,
)
from src.infra.repositories.meal_translation_repository import MealTranslationRepository


@pytest.fixture
def domain_translation():
    return MealTranslation(
        meal_id="meal-1",
        language="vi",
        dish_name="Phở",
        food_items=[
            FoodItemTranslation(food_item_id="fi-1", name="Bánh", description=None)
        ],
        translated_at=datetime(2024, 1, 1, 12, 0, 0),
        meal_instruction=[{"instruction": "Boil", "duration_minutes": 5}],
        meal_ingredients=["nước", "bánh"],
    )


def _make_session():
    return MagicMock()


def test_get_by_meal_and_language_returns_none():
    session = _make_session()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = None
    session.query.return_value = q

    repo = MealTranslationRepository(session_factory=lambda: session)
    assert repo.get_by_meal_and_language("m", "en") is None
    session.close.assert_called_once()


def test_get_by_meal_and_language_returns_domain(domain_translation):
    session = _make_session()
    db_row = MagicMock()
    db_row.to_domain.return_value = domain_translation
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = db_row
    session.query.return_value = q

    repo = MealTranslationRepository(session_factory=lambda: session)
    out = repo.get_by_meal_and_language("meal-1", "vi")
    assert out is domain_translation
    session.close.assert_called_once()


def test_save_creates_new_when_no_existing(domain_translation):
    session = _make_session()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = None
    session.query.return_value = q

    db_translation = MagicMock()
    db_translation.to_domain.return_value = domain_translation

    with patch(
        "src.infra.repositories.meal_translation_repository.DBMealTranslation"
    ) as DBCls:
        DBCls.from_domain.return_value = db_translation
        repo = MealTranslationRepository(session_factory=lambda: session)
        out = repo.save(domain_translation)

    assert out is domain_translation
    session.add.assert_called_once_with(db_translation)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(db_translation)
    session.close.assert_called_once()


def test_save_updates_existing_replaces_food_items(domain_translation):
    session = _make_session()
    existing = MagicMock()
    existing.id = 42
    old_fi = MagicMock()
    existing.food_items = [old_fi]

    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = existing
    session.query.return_value = q

    existing.to_domain.return_value = domain_translation

    repo = MealTranslationRepository(session_factory=lambda: session)
    out = repo.save(domain_translation)

    session.delete.assert_called_once_with(old_fi)
    session.flush.assert_called_once()
    assert session.add.call_count >= 1
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(existing)
    assert out is domain_translation
    session.close.assert_called_once()


def test_save_rollbacks_and_raises_on_commit_failure(domain_translation):
    session = _make_session()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = None
    session.query.return_value = q

    db_translation = MagicMock()
    with patch(
        "src.infra.repositories.meal_translation_repository.DBMealTranslation"
    ) as DBCls:
        DBCls.from_domain.return_value = db_translation
        session.commit.side_effect = RuntimeError("commit failed")
        repo = MealTranslationRepository(session_factory=lambda: session)
        with pytest.raises(RuntimeError, match="commit failed"):
            repo.save(domain_translation)

    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_delete_by_meal_returns_count():
    session = _make_session()
    q = MagicMock()
    q.filter.return_value = q
    q.delete.return_value = 3
    session.query.return_value = q

    repo = MealTranslationRepository(session_factory=lambda: session)
    assert repo.delete_by_meal("meal-x") == 3
    session.commit.assert_called_once()
    session.close.assert_called_once()


def test_delete_by_meal_rollbacks_on_error():
    session = _make_session()
    q = MagicMock()
    q.filter.return_value = q
    q.delete.return_value = 1
    session.query.return_value = q
    session.commit.side_effect = OSError("disk")

    repo = MealTranslationRepository(session_factory=lambda: session)
    with pytest.raises(OSError):
        repo.delete_by_meal("meal-x")

    session.rollback.assert_called_once()
    session.close.assert_called_once()
