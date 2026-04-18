"""Tests that MealRepository projection parameter controls relationship loading."""
from unittest.mock import MagicMock
from datetime import date

import pytest

from src.infra.repositories.meal_repository import MealRepository, MealProjection


def _make_repo():
    session = MagicMock()
    session.query.return_value.options.return_value.filter.return_value\
        .filter.return_value.filter.return_value.order_by.return_value\
        .limit.return_value.all.return_value = []
    session.query.return_value.options.return_value.filter.return_value\
        .first.return_value = None
    return MealRepository(session)


def test_meal_projection_enum_exists():
    """MealProjection enum must have MACROS_ONLY, FULL, FULL_WITH_TRANSLATIONS."""
    assert hasattr(MealProjection, "MACROS_ONLY")
    assert hasattr(MealProjection, "FULL")
    assert hasattr(MealProjection, "FULL_WITH_TRANSLATIONS")


def test_find_by_date_accepts_projection_parameter():
    """find_by_date must accept a projection keyword argument without error."""
    repo = _make_repo()
    # Should not raise TypeError
    repo.find_by_date(date(2026, 4, 18), user_id="u1", projection=MealProjection.MACROS_ONLY)


def test_find_by_id_accepts_projection_parameter():
    """find_by_id must accept a projection keyword argument without error."""
    repo = _make_repo()
    repo.find_by_id("meal-1", projection=MealProjection.FULL_WITH_TRANSLATIONS)


def test_projection_opt_counts():
    """Each projection must have the correct number of load options."""
    from src.infra.repositories.meal_repository import _PROJECTION_OPTS, MealProjection

    # MACROS_ONLY: nutrition + food_items selectinload (counts as 1 chained option)
    assert len(_PROJECTION_OPTS[MealProjection.MACROS_ONLY]) == 1, (
        "MACROS_ONLY must have 1 load option (nutrition chain)"
    )
    # FULL: image + nutrition chain
    assert len(_PROJECTION_OPTS[MealProjection.FULL]) == 2, (
        "FULL must have 2 load options (image, nutrition chain)"
    )
    # FULL_WITH_TRANSLATIONS: image + nutrition chain + translations
    assert len(_PROJECTION_OPTS[MealProjection.FULL_WITH_TRANSLATIONS]) == 3, (
        "FULL_WITH_TRANSLATIONS must have 3 load options (image, nutrition chain, translations)"
    )
