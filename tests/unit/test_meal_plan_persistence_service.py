"""
Unit tests for MealPlanPersistenceService.
"""
import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from src.app.handlers.shared.meal_plan_persistence_service import MealPlanPersistenceService
from src.domain.model import UserPreferences, DietaryPreference, FitnessGoal, PlanDuration
from src.infra.database.models.meal_planning import MealPlan as MealPlanORM


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def service(mock_db_session):
    """Create MealPlanPersistenceService instance."""
    return MealPlanPersistenceService(db=mock_db_session)


@pytest.fixture
def user_preferences():
    """Create sample user preferences."""
    return UserPreferences(
        dietary_preferences=[DietaryPreference.VEGETARIAN],
        allergies=["peanuts", "shellfish"],
        fitness_goal=FitnessGoal.MAINTENANCE,
        meals_per_day=3,
        snacks_per_day=1,
        cooking_time_weekday=30,
        cooking_time_weekend=60,
        favorite_cuisines=["Italian", "Mexican"],
        disliked_ingredients=["cilantro"],
        plan_duration=PlanDuration.DAILY
    )


class TestMealPlanPersistenceService:
    """Test suite for MealPlanPersistenceService."""

    def test_save_daily_meal_plan(self, service, mock_db_session, user_preferences):
        """Test saving a daily meal plan."""
        meal_plan_data = {
            "meals": [
                {
                    "meal_type": "breakfast",
                    "name": "Oatmeal Bowl",
                    "description": "Healthy breakfast",
                    "calories": 400,
                    "protein": 20.0,
                    "carbs": 60.0,
                    "fat": 10.0,
                    "prep_time": 5,
                    "cook_time": 10,
                    "ingredients": ["100g oats", "1 banana", "15ml honey"],
                    "seasonings": ["1g cinnamon"],
                    "instructions": ["Cook oats", "Add toppings"],
                    "is_vegetarian": True,
                    "is_vegan": False,
                    "is_gluten_free": True,
                    "cuisine_type": "International"
                },
                {
                    "meal_type": "lunch",
                    "name": "Veggie Wrap",
                    "description": "Fresh wrap",
                    "calories": 500,
                    "protein": 25.0,
                    "carbs": 65.0,
                    "fat": 15.0,
                    "prep_time": 10,
                    "cook_time": 0,
                    "ingredients": ["1 tortilla", "100g vegetables"],
                    "seasonings": ["2g salt", "1g pepper"],
                    "instructions": ["Wrap ingredients"],
                    "is_vegetarian": True,
                    "is_vegan": True,
                    "is_gluten_free": False,
                    "cuisine_type": "Mexican"
                }
            ]
        }
        
        # Mock ORM objects
        mock_meal_plan = Mock(spec=MealPlanORM)
        mock_meal_plan.id = "plan-123"
        
        # Setup mock behaviors
        mock_db_session.add = Mock()
        mock_db_session.flush = Mock()
        mock_db_session.commit = Mock()
        
        # Mock add to capture the meal plan
        def capture_meal_plan(obj):
            if isinstance(obj, type(mock_meal_plan)):
                mock_db_session.flush()
        mock_db_session.add.side_effect = capture_meal_plan
        
        # Execute
        plan_id = service.save_daily_meal_plan(meal_plan_data, user_preferences, "user-456")
        
        # Verify
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        # The plan_id should be a string (from mock)
        assert plan_id is not None

    def test_save_weekly_meal_plan(self, service, mock_db_session, user_preferences):
        """Test saving a weekly meal plan."""
        # Update preferences for weekly plan
        user_preferences.plan_duration = PlanDuration.WEEKLY
        
        plan_json = {
            "days": {
                "monday": [
                    {
                        "meal_type": "breakfast",
                        "name": "Monday Breakfast",
                        "description": "Start the week",
                        "calories": 450,
                        "protein": 25.0,
                        "carbs": 55.0,
                        "fat": 12.0,
                        "prep_time": 10,
                        "cook_time": 15,
                        "ingredients": ["200g eggs", "50g cheese"],
                        "seasonings": ["2g salt"],
                        "instructions": ["Cook eggs", "Add cheese"],
                        "is_vegetarian": True,
                        "is_vegan": False,
                        "is_gluten_free": True,
                        "cuisine_type": "American"
                    }
                ],
                "tuesday": [
                    {
                        "meal_type": "breakfast",
                        "name": "Tuesday Breakfast",
                        "description": "Nutritious start",
                        "calories": 400,
                        "protein": 20.0,
                        "carbs": 50.0,
                        "fat": 10.0,
                        "prep_time": 5,
                        "cook_time": 10,
                        "ingredients": ["100g oats", "1 banana"],
                        "seasonings": ["1g cinnamon"],
                        "instructions": ["Cook oats"],
                        "is_vegetarian": True,
                        "is_vegan": True,
                        "is_gluten_free": False,
                        "cuisine_type": "International"
                    }
                ]
            }
        }
        
        # Mock ORM objects
        mock_meal_plan = Mock(spec=MealPlanORM)
        mock_meal_plan.id = "plan-weekly-123"
        
        mock_db_session.add = Mock()
        mock_db_session.flush = Mock()
        mock_db_session.commit = Mock()
        
        # Execute
        plan_id = service.save_weekly_meal_plan(plan_json, user_preferences, "user-789")
        
        # Verify
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert plan_id is not None

    def test_meal_dict_to_orm_data(self, service):
        """Test converting meal dictionary to ORM data."""
        meal_data = {
            "meal_type": "dinner",
            "name": "Pasta Primavera",
            "description": "Fresh vegetable pasta",
            "calories": 550,
            "protein": 18.0,
            "carbs": 75.0,
            "fat": 20.0,
            "prep_time": 15,
            "cook_time": 20,
            "ingredients": ["200g pasta", "150g vegetables", "30ml olive oil"],
            "seasonings": ["3g salt", "2g pepper", "5g basil"],
            "instructions": ["Boil pasta", "Sauté vegetables", "Mix together"],
            "is_vegetarian": True,
            "is_vegan": True,
            "is_gluten_free": False,
            "cuisine_type": "Italian"
        }
        
        result = service._meal_dict_to_orm_data(meal_data)
        
        assert result["name"] == "Pasta Primavera"
        assert result["description"] == "Fresh vegetable pasta"
        assert result["calories"] == 550
        assert result["protein"] == 18.0
        assert result["carbs"] == 75.0
        assert result["fat"] == 20.0
        assert result["prep_time"] == 15
        assert result["cook_time"] == 20
        assert result["ingredients"] == ["200g pasta", "150g vegetables", "30ml olive oil"]
        assert result["seasonings"] == ["3g salt", "2g pepper", "5g basil"]
        assert result["instructions"] == ["Boil pasta", "Sauté vegetables", "Mix together"]
        assert result["is_vegetarian"] is True
        assert result["is_vegan"] is True
        assert result["is_gluten_free"] is False
        assert result["cuisine_type"] == "Italian"

    def test_meal_dict_to_orm_data_with_defaults(self, service):
        """Test converting meal dict with missing fields uses defaults."""
        meal_data = {
            "meal_type": "snack"
        }
        
        result = service._meal_dict_to_orm_data(meal_data)
        
        assert result["name"] == "Unnamed meal"
        assert result["description"] == ""
        assert result["calories"] == 0
        assert result["protein"] == 0.0
        assert result["carbs"] == 0.0
        assert result["fat"] == 0.0
        assert result["prep_time"] == 0
        assert result["cook_time"] == 0
        assert result["ingredients"] == []
        assert result["seasonings"] == []
        assert result["instructions"] == []
        assert result["is_vegetarian"] is False
        assert result["is_vegan"] is False
        assert result["is_gluten_free"] is False
        assert result["cuisine_type"] == "International"

    def test_meal_dict_to_orm_data_invalid_meal_type(self, service):
        """Test handling invalid meal type."""
        meal_data = {
            "meal_type": "invalid_type",
            "name": "Test Meal"
        }
        
        result = service._meal_dict_to_orm_data(meal_data)
        
        # Should default to breakfast
        from src.infra.database.models.enums import MealTypeEnum
        assert result["meal_type"] == MealTypeEnum.breakfast

    def test_meal_dict_to_orm_data_missing_meal_type(self, service):
        """Test handling missing meal type."""
        meal_data = {
            "name": "Test Meal"
        }
        
        result = service._meal_dict_to_orm_data(meal_data)
        
        # Should default to breakfast
        from src.infra.database.models.enums import MealTypeEnum
        assert result["meal_type"] == MealTypeEnum.breakfast

    def test_save_daily_meal_plan_rollback_on_error(self, service, mock_db_session, user_preferences):
        """Test that database rolls back on error."""
        meal_plan_data = {"meals": []}
        
        # Make commit raise an exception
        mock_db_session.commit.side_effect = Exception("Database error")
        mock_db_session.rollback = Mock()
        
        with pytest.raises(Exception, match="Database error"):
            service.save_daily_meal_plan(meal_plan_data, user_preferences, "user-error")
        
        assert mock_db_session.rollback.called

    def test_save_weekly_meal_plan_rollback_on_error(self, service, mock_db_session, user_preferences):
        """Test weekly plan rollback on error."""
        plan_json = {"days": {}}
        user_preferences.plan_duration = PlanDuration.WEEKLY
        
        mock_db_session.commit.side_effect = Exception("Database error")
        mock_db_session.rollback = Mock()
        
        with pytest.raises(Exception, match="Database error"):
            service.save_weekly_meal_plan(plan_json, user_preferences, "user-error")
        
        assert mock_db_session.rollback.called

    def test_save_weekly_meal_plan_with_all_days(self, service, mock_db_session, user_preferences):
        """Test saving weekly plan with all 7 days."""
        user_preferences.plan_duration = PlanDuration.WEEKLY
        
        # Create meals for all 7 days
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        plan_json = {
            "days": {
                day: [
                    {
                        "meal_type": "breakfast",
                        "name": f"{day.title()} Breakfast",
                        "description": "Daily breakfast",
                        "calories": 400,
                        "protein": 20.0,
                        "carbs": 50.0,
                        "fat": 10.0,
                        "prep_time": 10,
                        "cook_time": 10,
                        "ingredients": ["ingredients"],
                        "seasonings": ["seasonings"],
                        "instructions": ["instructions"],
                        "is_vegetarian": True,
                        "is_vegan": False,
                        "is_gluten_free": False,
                        "cuisine_type": "International"
                    }
                ]
                for day in days
            }
        }
        
        mock_meal_plan = Mock(spec=MealPlanORM)
        mock_meal_plan.id = "plan-full-week"
        
        mock_db_session.add = Mock()
        mock_db_session.flush = Mock()
        mock_db_session.commit = Mock()
        
        plan_id = service.save_weekly_meal_plan(plan_json, user_preferences, "user-full")
        
        # Verify all days were processed
        assert mock_db_session.add.call_count >= 8  # 1 plan + 7 days (minimum)
        assert mock_db_session.commit.called

    def test_save_daily_meal_plan_with_empty_meals(self, service, mock_db_session, user_preferences):
        """Test saving daily plan with no meals."""
        meal_plan_data = {"meals": []}
        
        mock_meal_plan = Mock(spec=MealPlanORM)
        mock_meal_plan.id = "plan-empty"
        
        mock_db_session.add = Mock()
        mock_db_session.flush = Mock()
        mock_db_session.commit = Mock()
        
        plan_id = service.save_daily_meal_plan(meal_plan_data, user_preferences, "user-empty")
        
        # Should still create plan and day, just no meals
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

