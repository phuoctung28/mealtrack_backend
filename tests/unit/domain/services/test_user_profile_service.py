"""Unit tests for UserProfileService."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.domain.services.user_profile_service import UserProfileService
from src.domain.model.meal_planning import (
    DietaryPreference,
    FitnessGoal,
    PlanDuration,
)
from src.domain.model.nutrition import Macros


@pytest.fixture
def mock_user_repo():
    return MagicMock()


@pytest.fixture
def mock_tdee_service():
    return MagicMock()


@pytest.fixture
def service(mock_user_repo, mock_tdee_service):
    return UserProfileService(mock_user_repo, mock_tdee_service)


class TestGetUserProfileOrDefaults:
    """Tests for get_user_profile_or_defaults method."""

    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_profile(self, service, mock_user_repo):
        """Should return default values when user has no profile."""
        mock_user_repo.get_profile.return_value = None

        result = await service.get_user_profile_or_defaults("user_123")

        assert result["target_calories"] == 2000
        assert result["target_protein"] == 150
        assert result["target_carbs"] == 250
        assert result["target_fat"] == 70
        assert result["meals_per_day"] == 3
        assert result["include_snacks"] is True
        assert result["dietary_preferences"] == []
        assert result["allergies"] == []

    @pytest.mark.asyncio
    async def test_returns_profile_data_with_tdee(
        self, service, mock_user_repo, mock_tdee_service
    ):
        """Should calculate TDEE and return profile data when profile exists."""
        mock_profile = MagicMock()
        mock_profile.gender = "male"
        mock_profile.age = 30
        mock_profile.height_cm = 175
        mock_profile.weight_kg = 75
        mock_profile.job_type = "desk"
        mock_profile.training_days_per_week = 4
        mock_profile.training_minutes_per_session = 60
        mock_profile.training_level = "intermediate"
        mock_profile.fitness_goal = "bulk"
        mock_profile.body_fat_percentage = 15
        mock_profile.dietary_preferences = ["vegetarian"]
        mock_profile.allergies = ["peanuts"]
        mock_profile.meals_per_day = 4
        mock_profile.snacks_per_day = 1
        mock_profile.health_conditions = []

        mock_user_repo.get_profile.return_value = mock_profile

        mock_macros = Macros(protein=180, carbs=300, fat=80, fiber=0, sugar=0)
        mock_tdee_result = MagicMock()
        mock_tdee_result.macros = mock_macros
        mock_tdee_service.calculate_tdee.return_value = mock_tdee_result

        result = await service.get_user_profile_or_defaults("user_123")

        assert result["target_protein"] == 180
        assert result["target_carbs"] == 300
        assert result["target_fat"] == 80
        assert result["target_calories"] == mock_macros.total_calories
        assert result["dietary_preferences"] == ["vegetarian"]
        assert result["allergies"] == ["peanuts"]
        assert result["meals_per_day"] == 4
        mock_tdee_service.calculate_tdee.assert_called_once()

    @pytest.mark.asyncio
    async def test_female_gender_mapping(
        self, service, mock_user_repo, mock_tdee_service
    ):
        """Should correctly map female gender."""
        mock_profile = MagicMock()
        mock_profile.gender = "female"
        mock_profile.age = 25
        mock_profile.height_cm = 165
        mock_profile.weight_kg = 60
        mock_profile.job_type = "active"
        mock_profile.training_days_per_week = 3
        mock_profile.training_minutes_per_session = 45
        mock_profile.training_level = "beginner"
        mock_profile.fitness_goal = "cut"
        mock_profile.body_fat_percentage = 25
        mock_profile.dietary_preferences = None
        mock_profile.allergies = None
        mock_profile.meals_per_day = 3
        mock_profile.snacks_per_day = 0
        mock_profile.health_conditions = None

        mock_user_repo.get_profile.return_value = mock_profile

        mock_macros = Macros(protein=120, carbs=150, fat=50, fiber=0, sugar=0)
        mock_tdee_result = MagicMock()
        mock_tdee_result.macros = mock_macros
        mock_tdee_service.calculate_tdee.return_value = mock_tdee_result

        result = await service.get_user_profile_or_defaults("user_456")

        assert result["include_snacks"] is False
        assert result["dietary_preferences"] == []
        assert result["health_conditions"] == []


class TestCreateUserPreferencesFromData:
    """Tests for create_user_preferences_from_data method."""

    def test_creates_preferences_with_valid_data(self, service):
        """Should create UserPreferences from valid data."""
        data = {
            "dietary_preferences": ["vegetarian", "gluten_free"],
            "allergies": ["nuts", "dairy"],
            "fitness_goal": "bulk",
            "meals_per_day": 4,
            "include_snacks": True,
            "favorite_cuisines": ["italian", "asian"],
            "disliked_ingredients": ["cilantro"],
        }

        result = service.create_user_preferences_from_data(data)

        assert DietaryPreference.VEGETARIAN in result.dietary_preferences
        assert DietaryPreference.GLUTEN_FREE in result.dietary_preferences
        assert result.allergies == ["nuts", "dairy"]
        assert result.fitness_goal == FitnessGoal.BULK
        assert result.meals_per_day == 4
        assert result.snacks_per_day == 1
        assert result.plan_duration == PlanDuration.DAILY

    def test_creates_preferences_with_custom_duration(self, service):
        """Should use provided plan duration."""
        data = {"fitness_goal": "recomp"}

        result = service.create_user_preferences_from_data(
            data, plan_duration=PlanDuration.WEEKLY
        )

        assert result.plan_duration == PlanDuration.WEEKLY

    def test_skips_unknown_dietary_preferences(self, service):
        """Should skip unknown dietary preferences with warning."""
        data = {
            "dietary_preferences": ["vegetarian", "unknown_pref", "vegan"],
            "fitness_goal": "cut",
        }

        result = service.create_user_preferences_from_data(data)

        assert len(result.dietary_preferences) == 2
        assert DietaryPreference.VEGETARIAN in result.dietary_preferences
        assert DietaryPreference.VEGAN in result.dietary_preferences

    def test_uses_defaults_for_missing_data(self, service):
        """Should use defaults when data is missing."""
        data = {}

        result = service.create_user_preferences_from_data(data)

        assert result.dietary_preferences == []
        assert result.allergies == []
        assert result.fitness_goal == FitnessGoal.RECOMP
        assert result.meals_per_day == 3
        assert result.snacks_per_day == 0
        assert result.cooking_time_weekday == 30
        assert result.cooking_time_weekend == 45
