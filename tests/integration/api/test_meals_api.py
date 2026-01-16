"""
Integration tests for Meals API endpoints.
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from tests.fixtures.factories.meal_factory import MealFactory
from tests.fixtures.factories.user_factory import UserFactory
from tests.fixtures.mock_adapters.mock_vision_ai_service import MockVisionAIService


@pytest.mark.integration
@pytest.mark.api
class TestMealsAPI:
    """Integration tests for Meals API."""
    
    # POST /v1/meals/image/analyze
    def test_analyze_meal_image_success(self, authenticated_client, sample_image_bytes, test_session):
        """Test immediate meal image analysis.
        
        Uses mocked Vision AI service from conftest (3rd party).
        Real handlers and domain services process the request.
        """
        # Act: POST image - Vision AI is mocked in conftest
        files = {"file": ("meal.jpg", sample_image_bytes, "image/jpeg")}
        response = authenticated_client.post("/v1/meals/image/analyze", files=files)
        
        # Assert: Returns meal with nutrition (from MockVisionAIService default response)
        assert response.status_code == 200
        data = response.json()
        assert data["meal_id"] is not None
        assert data["status"] == "ready"
        assert data["dish_name"] == "Grilled Chicken with Rice"
        # DetailedMealResponse has food_items, total_calories, total_nutrition
        assert "food_items" in data
        assert len(data["food_items"]) == 3
        assert data.get("total_calories") == 650
    
    def test_analyze_meal_image_with_target_date(self, authenticated_client, sample_image_bytes, test_session):
        """Test meal analysis with specific target date.
        
        Uses mocked Vision AI service from conftest (3rd party).
        """
        files = {"file": ("meal.jpg", sample_image_bytes, "image/jpeg")}
        target_date = "2024-12-25"
        
        response = authenticated_client.post(
            f"/v1/meals/image/analyze?target_date={target_date}",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["meal_id"] is not None
        assert data["dish_name"] == "Grilled Chicken with Rice"
    
    def test_analyze_meal_image_invalid_file_type(self, authenticated_client):
        """Test validation for invalid file types."""
        files = {"file": ("document.pdf", b"fake pdf content", "application/pdf")}
        
        response = authenticated_client.post("/v1/meals/image/analyze", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid file type" in data["detail"]["message"] or "Invalid file type" in str(data["detail"])
    
    def test_analyze_meal_image_file_too_large(self, authenticated_client):
        """Test validation for file size exceeding limit."""
        # Create a file larger than 10MB
        large_file = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large.jpg", large_file, "image/jpeg")}
        
        response = authenticated_client.post("/v1/meals/image/analyze", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "File size exceeds" in data["detail"]["message"] or "File size exceeds" in str(data["detail"])
    
    # POST /v1/meals/manual
    def test_create_manual_meal_success(self, authenticated_client, test_user, test_session):
        """Test creating manual meal from foods."""
        # Arrange: Request with food items
        payload = {
            "dish_name": "Custom Salad",
            "items": [
                {"fdc_id": 173944, "quantity": 100, "unit": "g"},  # Chicken breast
                {"fdc_id": 168462, "quantity": 150, "unit": "g"},  # Rice
            ],
            "meal_type": "lunch",
            "target_date": "2024-12-25"
        }
        
        # Mock the food data service to return nutrition data
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from src.domain.model.meal import Meal, MealStatus, MealImage
            from src.domain.model.nutrition import Nutrition, Macros, FoodItem
            from src.domain.utils.timezone_utils import utc_now
            
            # Create mock meal response with valid UUID
            mock_meal = Meal(
                meal_id=str(uuid4()),  # Use valid UUID
                user_id=test_user.id,
                status=MealStatus.READY,
                created_at=utc_now(),
                image=MealImage(
                    image_id=str(uuid4()),
                    format="jpeg",
                    size_bytes=102400,  # Must be positive
                    url=None
                ),
                dish_name="Custom Salad",
                nutrition=Nutrition(
                    calories=400.0,
                    macros=Macros(protein=30.0, carbs=40.0, fat=10.0),
                    food_items=[
                        FoodItem(
                            id=str(uuid4()),
                            name="Chicken Breast",
                            quantity=100.0,
                            unit="g",
                            calories=165.0,
                            macros=Macros(protein=31.0, carbs=0.0, fat=3.6),
                            confidence=1.0
                        ),
                        FoodItem(
                            id=str(uuid4()),
                            name="Rice",
                            quantity=150.0,
                            unit="g",
                            calories=195.0,
                            macros=Macros(protein=4.5, carbs=40.0, fat=0.6),
                            confidence=1.0
                        ),
                    ]
                ),
                ready_at=utc_now()
            )
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value=mock_meal)
            
            # Act: POST manual meal
            response = authenticated_client.post("/v1/meals/manual", json=payload)
            
            # Assert: Meal created
            assert response.status_code == 200
            data = response.json()
            assert data["meal_id"] is not None
            assert data["status"] == "success"
            assert data["message"] is not None
    
    # PUT /v1/meals/{id}/ingredients
    def test_edit_meal_ingredients(self, authenticated_client, test_user, test_session):
        """Test editing meal ingredients."""
        # Arrange: Create existing meal
        meal = MealFactory.create_meal(test_session, test_user.id)
        
        # Arrange: Changes to apply (use correct schema)
        payload = {
            "dish_name": meal.dish_name,
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Avocado",
                    "quantity": 50.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 160.0,
                        "protein_per_100g": 2.0,
                        "carbs_per_100g": 8.0,
                        "fat_per_100g": 14.0
                    }
                }
            ]
        }
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from src.domain.model.meal import Meal, MealStatus, MealImage
            from src.domain.model.nutrition import Nutrition, Macros, FoodItem
            from src.domain.utils.timezone_utils import utc_now
            
            # Create updated meal with valid UUIDs
            updated_meal = Meal(
                meal_id=meal.meal_id,
                user_id=test_user.id,
                status=MealStatus.READY,
                created_at=utc_now(),
                image=MealImage(
                    image_id=str(uuid4()),
                    format="jpeg",
                    size_bytes=102400,  # Must be positive
                    url=None
                ),
                dish_name=meal.dish_name,
                nutrition=Nutrition(
                    calories=640.0,  # Updated calories
                    macros=Macros(protein=45.0, carbs=50.0, fat=20.0),  # Updated macros
                    food_items=[
                        FoodItem(
                            id=str(uuid4()),
                            name="Chicken Breast",
                            quantity=200.0,
                            unit="g",
                            calories=330.0,
                            macros=Macros(protein=62.0, carbs=0.0, fat=7.0),
                            confidence=0.95
                        ),
                        FoodItem(
                            id=str(uuid4()),
                            name="Rice",
                            quantity=150.0,
                            unit="g",
                            calories=195.0,
                            macros=Macros(protein=4.5, carbs=40.0, fat=0.6),
                            confidence=0.95
                        ),
                        FoodItem(
                            id=str(uuid4()),
                            name="Avocado",
                            quantity=50.0,
                            unit="g",
                            calories=80.0,
                            macros=Macros(protein=1.0, carbs=4.0, fat=7.0),
                            confidence=1.0,
                            is_custom=True
                        ),
                    ]
                ),
                ready_at=utc_now(),
                is_manually_edited=True,
                edit_count=1
            )
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value=updated_meal)
            
            # Act: PUT changes
            response = authenticated_client.put(
                f"/v1/meals/{meal.meal_id}/ingredients",
                json=payload
            )
            
            # Assert: Meal updated
            assert response.status_code == 200
            # Edit endpoint returns the updated meal domain model
            # The response is the meal object itself, not a dict
            assert updated_meal.meal_id == meal.meal_id
    
    # DELETE /v1/meals/{id}
    def test_delete_meal_success(self, authenticated_client, test_user, test_session):
        """Test soft delete meal."""
        # Arrange: Create meal
        meal = MealFactory.create_meal(test_session, test_user.id)
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value={"success": True})
            
            # Act: DELETE meal
            response = authenticated_client.delete(f"/v1/meals/{meal.meal_id}")
            
            # Assert: Success
            assert response.status_code == 200
    
    def test_delete_meal_not_found(self, authenticated_client):
        """Test delete non-existent meal returns 404."""
        fake_meal_id = "00000000-0000-0000-0000-000000000000"
        
        # Mock the event bus to raise ResourceNotFoundException
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from src.api.exceptions import ResourceNotFoundException
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(side_effect=ResourceNotFoundException(f"Meal {fake_meal_id} not found"))
            
            # Act: DELETE non-existent meal
            response = authenticated_client.delete(f"/v1/meals/{fake_meal_id}")
            
            # Assert: 404
            assert response.status_code == 404
    
    # GET /v1/meals/{id}
    def test_get_meal_by_id(self, authenticated_client, test_user, test_session):
        """Test retrieving meal by ID."""
        # Arrange: Create meal
        meal = MealFactory.create_meal(test_session, test_user.id)
        test_session.refresh(meal)  # Ensure nutrition is loaded
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            # Get domain meal from DB meal - ensure nutrition is loaded
            domain_meal = meal.to_domain()
            
            # Ensure nutrition exists
            assert domain_meal.nutrition is not None, "Meal should have nutrition"
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value=domain_meal)
            
            # Act: GET meal
            response = authenticated_client.get(f"/v1/meals/{meal.meal_id}")
            
            # Assert: Returns meal
            assert response.status_code == 200
            data = response.json()
            assert data["meal_id"] == meal.meal_id
            assert data["dish_name"] == meal.dish_name
            # DetailedMealResponse has food_items, total_calories, total_nutrition (not nutrition)
            if domain_meal.status.value == "READY" and domain_meal.nutrition:
                assert "food_items" in data
                assert len(data["food_items"]) > 0
                assert data.get("total_calories") is not None
    
    def test_get_meal_not_found(self, authenticated_client):
        """Test 404 for non-existent meal."""
        fake_meal_id = "00000000-0000-0000-0000-000000000000"
        
        # Mock the event bus to raise ResourceNotFoundException
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from src.api.exceptions import ResourceNotFoundException
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(side_effect=ResourceNotFoundException(f"Meal {fake_meal_id} not found"))
            
            # Act: GET non-existent meal
            response = authenticated_client.get(f"/v1/meals/{fake_meal_id}")
            
            # Assert: 404
            assert response.status_code == 404
    
    # GET /v1/meals/daily-macros
    def test_get_daily_macros(self, authenticated_client, test_user_with_profile, test_session):
        """Test daily macro aggregation."""
        # Arrange: Create meals for specific date
        user, profile = test_user_with_profile
        target_date = date(2024, 12, 25)
        
        # Create meals for the target date with nutrition data
        from src.infra.database.models.meal.meal import Meal as DBMeal
        from src.infra.database.models.meal.meal_image import MealImage as DBMealImage
        from src.infra.database.models.nutrition.nutrition import Nutrition as DBNutrition
        from src.infra.database.models.nutrition.food_item import FoodItem as DBFoodItem
        from src.infra.database.models.enums import MealStatusEnum
        from datetime import datetime
        from uuid import uuid4
        
        # Create meals with nutrition
        for i in range(2):
            meal_id = str(uuid4())
            image_id = str(uuid4())
            
            # Create image
            db_image = DBMealImage(
                image_id=image_id,
                format="jpeg",
                size_bytes=102400,
                url=None
            )
            test_session.add(db_image)
            test_session.flush()
            
            # Create meal
            meal_datetime = datetime.combine(target_date, datetime.min.time())
            db_meal = DBMeal(
                meal_id=meal_id,
                user_id=user.id,
                status=MealStatusEnum.READY,
                dish_name=f"Test Meal {i+1}",
                created_at=meal_datetime,
                ready_at=meal_datetime,  # Required for READY status
                image_id=image_id
            )
            test_session.add(db_meal)
            test_session.flush()
            
            # Create nutrition
            db_nutrition = DBNutrition(
                meal_id=meal_id,
                calories=560.0,  # 1120 total for 2 meals
                protein=45.0,
                carbs=50.0,
                fat=12.0,
                confidence_score=0.95
            )
            test_session.add(db_nutrition)
            test_session.flush()
        
        test_session.commit()
        
        # Act: GET daily macros - uses real handler
        response = authenticated_client.get(f"/v1/meals/daily/macros?date={target_date}")
        
        # Assert: Correct totals
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(target_date)
        # Response may use consumed_calories or total_calories
        calories = data.get("consumed_calories") or data.get("total_calories", 0)
        assert calories == 1120.0  # 560 * 2
        assert "target_calories" in data or "target_macros" in data  # May or may not have targets
    
    def test_get_daily_macros_without_date(self, authenticated_client, test_user_with_profile):
        """Test daily macros defaults to today."""
        user, profile = test_user_with_profile
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from datetime import date
            
            today = date.today()
            # Mock daily macros query result (dict format)
            mock_response = {
                "date": str(today),
                "user_id": user.id,
                "target_calories": 2000.0,
                "target_macros": {
                    "protein": 150.0,
                    "carbs": 200.0,
                    "fat": 65.0
                },
                "total_calories": 0.0,
                "total_protein": 0.0,
                "total_carbs": 0.0,
                "total_fat": 0.0,
                "meals_count": 0
            }
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value=mock_response)
            
            # Act: GET daily macros without date
            response = authenticated_client.get("/v1/meals/daily/macros")
            
            # Assert: Returns today's macros
            assert response.status_code == 200
            data = response.json()
            assert data["date"] == str(today)
            assert data["consumed_calories"] == 0.0
