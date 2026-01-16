"""
Integration tests for Meal Plans API endpoints.
"""
import pytest
from datetime import date
from unittest.mock import patch, AsyncMock

from tests.fixtures.factories.user_factory import UserFactory


@pytest.mark.integration
@pytest.mark.api
class TestMealPlansAPI:
    """Integration tests for Meal Plans API."""
    
    # POST /v1/meal-plans/generate/weekly-ingredient-based
    def test_generate_weekly_meal_plan(self, authenticated_client, test_user_with_profile, test_session):
        """Test weekly meal plan generation."""
        # Arrange: Ingredients list
        user, profile = test_user_with_profile
        
        # Store user_id before session operations (to avoid DetachedInstanceError)
        user_id = str(user.id)
        
        # Ensure user and profile are attached to session
        test_session.refresh(user)
        test_session.refresh(profile)
        
        payload = {
            "available_ingredients": ["chicken", "rice", "broccoli", "carrots"],
            "available_seasonings": ["salt", "pepper", "garlic"]
        }
        
        # Act: POST generate - uses real handler
        response = authenticated_client.post(
            "/v1/meal-plans/generate/weekly-ingredient-based",
            json=payload
        )
        
        # Assert: Success status, plan created
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Weekly meal plan generated successfully!"
        assert data["user_id"] == user_id
    
    def test_generate_meal_plan_without_profile(self, authenticated_client, test_user, test_session):
        """Test generation works without user profile (uses defaults).
        
        Note: The handler uses get_user_profile_or_defaults which provides defaults
        if no profile exists, so it doesn't fail.
        """
        # Arrange: User without profile
        test_session.refresh(test_user)  # Ensure user is attached to session
        
        payload = {
            "available_ingredients": ["chicken", "rice"],
            "available_seasonings": ["salt", "pepper"]
        }
        
        # Act: POST generate - uses real handler (will use defaults)
        response = authenticated_client.post(
            "/v1/meal-plans/generate/weekly-ingredient-based",
            json=payload
        )
        
        # Assert: Success (handler uses defaults when no profile)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    # GET /v1/meal-plans/meals/by-date
    def test_get_meals_by_date(self, authenticated_client, test_user, test_session):
        """Test retrieving meals for specific date."""
        # Arrange: Mock meal plan
        meal_date = date(2024, 12, 25)
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = mock_get_bus.return_value
            
            from datetime import datetime
            meal_date_str = meal_date.strftime("%A, %B %d, %Y")
            
            mock_response = {
                "date": str(meal_date),
                "day_formatted": meal_date_str,
                "user_id": test_user.id,
                "total_meals": 2,
                "meals": [
                    {
                        "meal_id": "meal-1",
                        "name": "Breakfast Bowl",
                        "meal_type": "breakfast",
                        "description": "Healthy breakfast bowl",
                        "prep_time": 10,
                        "cook_time": 5,
                        "total_time": 15,
                        "calories": 400,
                        "protein": 20.0,
                        "carbs": 50.0,
                        "fat": 12.0,
                        "ingredients": ["Oats", "Berries", "Yogurt"],
                        "seasonings": [],
                        "instructions": ["Mix ingredients", "Serve"],
                        "is_vegetarian": True,
                        "is_vegan": False,
                        "is_gluten_free": True,
                        "cuisine_type": None
                    },
                    {
                        "meal_id": "meal-2",
                        "name": "Lunch Salad",
                        "meal_type": "lunch",
                        "description": "Fresh lunch salad",
                        "prep_time": 15,
                        "cook_time": 0,
                        "total_time": 15,
                        "calories": 500,
                        "protein": 30.0,
                        "carbs": 40.0,
                        "fat": 20.0,
                        "ingredients": ["Lettuce", "Chicken", "Tomatoes"],
                        "seasonings": ["Salt", "Pepper"],
                        "instructions": ["Chop vegetables", "Add chicken", "Toss"],
                        "is_vegetarian": False,
                        "is_vegan": False,
                        "is_gluten_free": True,
                        "cuisine_type": None
                    }
                ]
            }
            
            # Create test data: meal plan with planned meals
            from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
            from src.infra.database.models.meal_planning.meal_plan_day import MealPlanDay as DBMealPlanDay
            from src.infra.database.models.meal_planning.planned_meal import PlannedMeal as DBPlannedMeal
            from src.infra.database.models.enums import MealTypeEnum
            from uuid import uuid4
            
            # Store user_id before session operations (to avoid DetachedInstanceError)
            user_id = str(test_user.id)
            
            # Create meal plan
            plan = DBMealPlan(
                id=str(uuid4()),
                user_id=user_id,
                dietary_preferences=[],
                allergies=[],
                meals_per_day=3,
                snacks_per_day=1,
                cooking_time_weekday=30,
                cooking_time_weekend=45,
                favorite_cuisines=[],
                disliked_ingredients=[]
            )
            test_session.add(plan)
            test_session.flush()
            
            # Create meal plan day
            plan_day = DBMealPlanDay(
                meal_plan_id=plan.id,
                date=meal_date
            )
            test_session.add(plan_day)
            test_session.flush()
            
            # Create 2 planned meals
            for i in range(2):
                planned_meal = DBPlannedMeal(
                    day_id=plan_day.id,
                    meal_type=MealTypeEnum.breakfast if i == 0 else MealTypeEnum.lunch,
                    name=f"Test Meal {i+1}",
                    description="Test description",
                    calories=400.0 + i * 100,
                    protein=30.0,
                    carbs=40.0,
                    fat=20.0,
                    ingredients=["Test ingredient"],
                    instructions=["Test instruction"],
                    is_vegetarian=False,
                    is_vegan=False,
                    is_gluten_free=True
                )
                test_session.add(planned_meal)
            
            test_session.commit()
            
            # Act: GET meals by date - uses real handler
            response = authenticated_client.get(
                f"/v1/meal-plans/meals/by-date?meal_date={meal_date}"
            )
            
            # Assert: Returns meals for date
            assert response.status_code == 200
            data = response.json()
            assert data["date"] == str(meal_date)
            assert "meals" in data
            assert len(data["meals"]) == 2
            assert data["total_meals"] == 2
            assert data["user_id"] == user_id
    
    # GET /v1/meal-plans/{plan_id}
    def test_get_meal_plan_by_id(self, authenticated_client, test_user, test_session):
        """Test retrieving full meal plan."""
        # Create test data: meal plan
        from src.infra.database.models.meal_planning.meal_plan import MealPlan as DBMealPlan
        from uuid import uuid4
        
        # Ensure user is attached to session
        test_session.refresh(test_user)
        
        plan_id = str(uuid4())
        plan = DBMealPlan(
            id=plan_id,
            user_id=test_user.id,
            dietary_preferences=[],
            allergies=[],
            meals_per_day=3,
            snacks_per_day=1,
            cooking_time_weekday=30,
            cooking_time_weekend=45,
            favorite_cuisines=[],
            disliked_ingredients=[]
        )
        test_session.add(plan)
        test_session.commit()
        
        # Act: GET meal plan - uses real handler
        response = authenticated_client.get(f"/v1/meal-plans/{plan_id}")
        
        # Assert: Returns full meal plan (real handler response)
        # Handler returns {"meal_plan": {...}} structure
        assert response.status_code == 200
        data = response.json()
        # Handler wraps in "meal_plan" key
        if "meal_plan" in data:
            plan_data = data["meal_plan"]
            assert plan_data["plan_id"] == plan_id
        else:
            # Or might return directly
            assert data["plan_id"] == plan_id
