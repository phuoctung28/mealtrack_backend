import io

import httpx
import pytest

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30


@pytest.fixture
def client():
    """HTTP client for API testing."""
    return httpx.Client(base_url=BASE_URL, timeout=TEST_TIMEOUT)


@pytest.fixture
def sample_food_data():
    """Sample food data for testing."""
    return {
        "name": "Test Food Item",
        "brand": "Test Brand",
        "description": "A test food item for API testing",
        "serving_size": 100.0,
        "serving_unit": "g",
        "calories_per_serving": 250.0,
        "macros_per_serving": {
            "protein": 20.0,
            "carbs": 30.0,
            "fat": 10.0,
            "fiber": 5.0
        },
        "barcode": "1234567890123"
    }


@pytest.fixture
def sample_ingredient_data():
    """Sample ingredient data for testing."""
    return {
        "name": "Test Ingredient",
        "quantity": 50.0,
        "unit": "g",
        "calories": 100.0,
        "macros": {
            "protein": 10.0,
            "carbs": 15.0,
            "fat": 5.0,
            "fiber": 2.0
        }
    }


@pytest.fixture
def sample_onboarding_data():
    """Sample onboarding data for testing."""
    return {
        "age": 30,
        "gender": "male",
        "height": 180.0,
        "weight": 75.0,
        "activity_level": "moderately_active",
        "goal": "lose_weight",
        "timeline_months": 6
    }


@pytest.fixture
def sample_consumed_macros():
    """Sample consumed macros data for testing."""
    return {
        "calories": 300.0,
        "macros": {
            "protein": 25.0,
            "carbs": 35.0,
            "fat": 12.0,
            "fiber": 6.0
        },
        "meal_id": "test-meal-id"
    }


class TestHealthAndRoot:
    """Test health check and root endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MealTrack API"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert "available_endpoints" in data


class TestOnboardingEndpoints:
    """Test onboarding-related endpoints."""
    
    def test_get_onboarding_sections(self, client):
        """Test retrieving onboarding sections."""
        response = client.get("/v1/onboarding/sections")
        assert response.status_code == 200
        
        data = response.json()
        assert "sections" in data
        assert "total_sections" in data
        assert data["total_sections"] == 5
        
        # Verify section structure
        sections = data["sections"]
        assert len(sections) == 5
        
        for section in sections:
            assert "section_id" in section
            assert "title" in section
            assert "description" in section
            assert "section_type" in section
            assert "order" in section
            assert "fields" in section
            assert "is_active" in section
            
            # Verify fields structure
            for field in section["fields"]:
                assert "field_id" in field
                assert "label" in field
                assert "field_type" in field
                assert "required" in field
    
    def test_submit_onboarding_response(self, client):
        """Test submitting onboarding responses."""
        response_data = {
            "section_id": "personal-info",
            "field_responses": {
                "age": 30,
                "gender": "male",
                "height": 180,
                "weight": 75
            }
        }
        
        response = client.post("/v1/onboarding/responses", json=response_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "response_id" in data
        assert data["section_id"] == "personal-info"
        assert data["field_responses"] == response_data["field_responses"]


class TestActivitiesEndpoints:
    """Test activity-related endpoints."""
    
    def test_get_activities_default(self, client):
        """Test getting activities with default parameters."""
        response = client.get("/v1/activities/")
        assert response.status_code == 200
        
        data = response.json()
        assert "activities" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        
        # Verify activity structure
        for activity in data["activities"]:
            assert "activity_id" in activity
            assert "activity_type" in activity
            assert "title" in activity
            assert "created_at" in activity
    
    def test_get_activities_with_filters(self, client):
        """Test getting activities with filters."""
        params = {
            "activity_type": "MEAL_SCAN",
            "limit": 10,
            "offset": 0
        }
        
        response = client.get("/v1/activities/", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page_size"] == 10
        
        # All activities should be MEAL_SCAN type
        for activity in data["activities"]:
            assert activity["activity_type"] == "MEAL_SCAN"
    
    def test_get_activity_types(self, client):
        """Test getting available activity types."""
        response = client.get("/v1/activities/types")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        expected_types = ["MEAL_SCAN", "MANUAL_FOOD_ADD", "FOOD_UPDATE", "INGREDIENT_ADD", "MACRO_CALCULATION"]
        assert all(activity_type in expected_types for activity_type in data)
    
    def test_get_specific_activity(self, client):
        """Test getting a specific activity by ID."""
        activity_id = "test-activity-id"
        response = client.get(f"/v1/activities/{activity_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["activity_id"] == activity_id
        assert "activity_type" in data
        assert "title" in data


class TestFoodEndpoints:
    """Test food management endpoints."""
    
    def test_create_food(self, client, sample_food_data):
        """Test creating a new food item."""
        response = client.post("/v1/food/", json=sample_food_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "food_id" in data
        assert data["name"] == sample_food_data["name"]
        assert data["brand"] == sample_food_data["brand"]
        assert data["is_verified"] == False
    
    def test_get_food_by_id(self, client):
        """Test retrieving food by ID."""
        food_id = "test-food-id"
        response = client.get(f"/v1/food/{food_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["food_id"] == food_id
        assert "name" in data
        assert "macros_per_serving" in data
    
    def test_update_food(self, client):
        """Test updating food information."""
        food_id = "test-food-id"
        update_data = {
            "name": "Updated Food Name",
            "calories_per_serving": 300.0,
            "macros_per_serving": {
                "protein": 25.0,
                "carbs": 35.0,
                "fat": 12.0,
                "fiber": 6.0
            }
        }
        
        response = client.put(f"/v1/food/{food_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["food_id"] == food_id
        assert "updated_at" in data
    
    def test_update_food_macros_by_portion(self, client):
        """Test updating food macros based on portion size."""
        food_id = "test-food-id"
        macros_data = {
            "size": 150.0,
            "unit": "g"
        }
        
        response = client.post(f"/v1/food/{food_id}/macros", json=macros_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["food_id"] == food_id
        assert "original_serving" in data
        assert "adjusted_serving" in data
        assert "scaling_factor" in data
    
    def test_analyze_food_photo(self, client):
        """Test food photo analysis endpoint."""
        # Create a dummy image file for testing
        image_data = b"fake_image_data_for_testing"
        files = {
            "file": ("test_image.jpg", io.BytesIO(image_data), "image/jpeg")
        }
        
        response = client.post("/v1/food/photo", files=files)
        assert response.status_code == 201
        
        data = response.json()
        assert "food_name" in data
        assert "confidence" in data
        assert "macros" in data
        assert "calories" in data
        assert "analysis_id" in data
        assert 0 <= data["confidence"] <= 1
    
    def test_analyze_food_photo_invalid_file_type(self, client):
        """Test food photo analysis with invalid file type."""
        files = {
            "file": ("test_file.txt", io.BytesIO(b"not_an_image"), "text/plain")
        }
        
        response = client.post("/v1/food/photo", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestIngredientsEndpoints:
    """Test ingredient management endpoints."""
    
    def test_add_ingredient(self, client, sample_ingredient_data):
        """Test adding an ingredient to a food."""
        food_id = "test-food-id"
        response = client.post(f"/v1/food/{food_id}/ingredients/", json=sample_ingredient_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "ingredient" in data
        assert "message" in data
        assert "updated_food_macros" in data
        assert data["ingredient"]["food_id"] == food_id
        assert data["ingredient"]["name"] == sample_ingredient_data["name"]
    
    def test_get_ingredients(self, client):
        """Test getting all ingredients for a food."""
        food_id = "test-food-id"
        response = client.get(f"/v1/food/{food_id}/ingredients/")
        assert response.status_code == 200
        
        data = response.json()
        assert "ingredients" in data
        assert "total_count" in data
        assert data["food_id"] == food_id
        
        for ingredient in data["ingredients"]:
            assert ingredient["food_id"] == food_id
            assert "ingredient_id" in ingredient
            assert "name" in ingredient
            assert "quantity" in ingredient
            assert "unit" in ingredient
    
    def test_update_ingredient(self, client):
        """Test updating an ingredient."""
        food_id = "test-food-id"
        ingredient_id = "test-ingredient-id"
        update_data = {
            "name": "Updated Ingredient",
            "quantity": 75.0,
            "calories": 150.0
        }
        
        response = client.put(f"/v1/food/{food_id}/ingredients/{ingredient_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "ingredient" in data
        assert "message" in data
        assert "updated_food_macros" in data
        assert data["ingredient"]["ingredient_id"] == ingredient_id
    
    def test_delete_ingredient(self, client):
        """Test deleting an ingredient."""
        food_id = "test-food-id"
        ingredient_id = "test-ingredient-id"
        
        response = client.delete(f"/v1/food/{food_id}/ingredients/{ingredient_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "deleted_ingredient_id" in data
        assert "updated_food_macros" in data
        assert data["deleted_ingredient_id"] == ingredient_id


class TestMacrosEndpoints:
    """Test macros and nutrition tracking endpoints."""
    
    def test_calculate_macros_from_onboarding(self, client, sample_onboarding_data):
        """Test calculating macros from onboarding data."""
        response = client.post("/v1/macros/calculate", json=sample_onboarding_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "target_calories" in data
        assert "target_macros" in data
        assert "estimated_timeline_months" in data
        assert "bmr" in data
        assert "tdee" in data
        assert "daily_calorie_deficit_surplus" in data
        assert "recommendations" in data
        assert "user_macros_id" in data
        
        # Verify macros structure
        target_macros = data["target_macros"]
        assert "protein" in target_macros
        assert "carbs" in target_macros
        assert "fat" in target_macros
        assert "fiber" in target_macros
        
        # Verify recommendations
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
    
    def test_calculate_macros_invalid_data(self, client):
        """Test macro calculation with invalid data."""
        invalid_data = {
            "age": -5,  # Invalid age
            "gender": "invalid",  # Invalid gender
            "height": 0,  # Invalid height
            "weight": 0,  # Invalid weight
            "activity_level": "invalid",  # Invalid activity level
            "goal": "invalid"  # Invalid goal
        }
        
        response = client.post("/v1/macros/calculate", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_update_consumed_macros(self, client, sample_consumed_macros):
        """Test updating consumed macros."""
        response = client.post("/v1/macros/consumed", json=sample_consumed_macros)
        assert response.status_code == 200
        
        data = response.json()
        assert "user_macros_id" in data
        assert "target_date" in data
        assert "target_calories" in data
        assert "target_macros" in data
        assert "consumed_calories" in data
        assert "consumed_macros" in data
        assert "remaining_calories" in data
        assert "remaining_macros" in data
        assert "completion_percentage" in data
        assert "is_goal_met" in data
        assert "recommendations" in data
        
        # Verify completion percentage structure
        completion = data["completion_percentage"]
        assert "calories" in completion
        assert "protein" in completion
        assert "carbs" in completion
        assert "fat" in completion
    
    def test_get_daily_macros(self, client):
        """Test getting daily macros."""
        response = client.get("/v1/macros/daily")
        assert response.status_code == 200
        
        data = response.json()
        assert "date" in data
        assert "target_calories" in data
        assert "target_macros" in data
        assert "consumed_calories" in data
        assert "consumed_macros" in data
        assert "remaining_calories" in data
        assert "remaining_macros" in data
        assert "completion_percentage" in data
    
    def test_get_daily_macros_with_date(self, client):
        """Test getting daily macros for a specific date."""
        date = "2024-01-15"
        params = {"date": date}
        
        response = client.get("/v1/macros/daily", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data["date"] == date


class TestFoodDatabaseEndpoints:
    """Test food database endpoints."""
    
    def test_get_foods_list_default(self, client):
        """Test getting foods list with default parameters."""
        response = client.get("/v1/food-database/")
        assert response.status_code == 200
        
        data = response.json()
        assert "foods" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 20
        
        # Verify food structure
        for food in data["foods"]:
            assert "food_id" in food
            assert "name" in food
            assert "is_verified" in food
    
    def test_get_foods_list_with_pagination(self, client):
        """Test getting foods list with pagination."""
        params = {
            "page": 1,
            "page_size": 10,
            "verified_only": True
        }
        
        response = client.get("/v1/food-database/", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        # All foods should be verified
        for food in data["foods"]:
            assert food["is_verified"] == True
    
    def test_add_food_to_database(self, client, sample_food_data):
        """Test adding food to database."""
        response = client.post("/v1/food-database/", json=sample_food_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "food_id" in data
        assert data["name"] == sample_food_data["name"]
        assert data["is_verified"] == False  # New foods start unverified
    
    def test_search_foods(self, client):
        """Test searching foods in database."""
        search_data = {
            "query": "chicken",
            "limit": 5,
            "include_ingredients": False
        }
        
        response = client.post("/v1/food-database/search", json=search_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert data["query"] == search_data["query"]
        assert len(data["results"]) <= search_data["limit"]
        
        # Verify search results contain the query term
        for food in data["results"]:
            food_text = f"{food['name']} {food.get('brand', '')} {food.get('description', '')}".lower()
            assert "chicken" in food_text
    
    def test_search_foods_invalid_query(self, client):
        """Test searching with invalid query."""
        search_data = {
            "query": "",  # Empty query
            "limit": 5
        }
        
        response = client.post("/v1/food-database/search", json=search_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_popular_foods(self, client):
        """Test getting popular foods."""
        params = {"limit": 5}
        
        response = client.get("/v1/food-database/popular", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        
        for food in data:
            assert "food_id" in food
            assert "name" in food
            assert "is_verified" in food


class TestValidationAndErrors:
    """Test validation and error handling."""
    
    def test_invalid_food_id_format(self, client):
        """Test endpoints with invalid food ID format."""
        invalid_food_id = "invalid-id-format"
        
        # This should still work as the endpoints accept any string as food_id
        # The validation would happen at the service layer, not the API layer
        response = client.get(f"/v1/food/{invalid_food_id}")
        assert response.status_code == 200  # Endpoint works with placeholder data
    
    def test_missing_required_fields(self, client):
        """Test creating food without required fields."""
        incomplete_data = {
            # Missing required 'name' field
            "brand": "Test Brand"
        }
        
        response = client.post("/v1/food/", json=incomplete_data)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_macro_values(self, client):
        """Test with invalid macro values."""
        invalid_data = {
            "name": "Test Food",
            "macros_per_serving": {
                "protein": -10.0,  # Negative protein
                "carbs": 30.0,
                "fat": 10.0
            }
        }
        
        response = client.post("/v1/food/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_pagination_limits(self, client):
        """Test pagination with invalid limits."""
        params = {
            "page": 0,  # Invalid page number
            "page_size": 150  # Exceeds maximum page size
        }
        
        response = client.get("/v1/food-database/", params=params)
        assert response.status_code == 422  # Validation error


# Integration test to run all endpoints in sequence
class TestIntegrationFlow:
    """Test a complete user flow through multiple endpoints."""
    
    def test_complete_user_flow(self, client, sample_onboarding_data, sample_food_data, sample_consumed_macros):
        """Test a complete user flow from onboarding to macro tracking."""
        
        # 1. Get onboarding sections
        response = client.get("/v1/onboarding/sections")
        assert response.status_code == 200
        
        # 2. Calculate macros from onboarding
        response = client.post("/v1/macros/calculate", json=sample_onboarding_data)
        assert response.status_code == 201
        macro_data = response.json()
        
        # 3. Search for food in database
        search_data = {"query": "chicken", "limit": 5}
        response = client.post("/v1/food-database/search", json=search_data)
        assert response.status_code == 200
        
        # 4. Add a new food to database
        response = client.post("/v1/food-database/", json=sample_food_data)
        assert response.status_code == 201
        
        # 5. Update consumed macros
        response = client.post("/v1/macros/consumed", json=sample_consumed_macros)
        assert response.status_code == 200
        
        # 6. Check daily macros
        response = client.get("/v1/macros/daily")
        assert response.status_code == 200
        
        # 7. Get activities
        response = client.get("/v1/activities/")
        assert response.status_code == 200


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_api_endpoints.py -v
    pytest.main([__file__, "-v"]) 