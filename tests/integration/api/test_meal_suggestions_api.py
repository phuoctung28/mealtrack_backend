"""
Integration tests for Meal Suggestions API endpoints.

Tests use mocked 3rd party services (AI generation, Redis) from conftest.
Real application handlers and domain services process the requests.
"""
import pytest


@pytest.mark.integration
@pytest.mark.api
class TestMealSuggestionsAPI:
    """Integration tests for Meal Suggestions API.
    
    3rd party services (AI, Redis) are mocked in conftest.
    Real handlers and domain services process requests.
    """
    
    # POST /v1/meal-suggestions/generate
    def test_generate_suggestions_initial(self, authenticated_client, test_user_with_profile, test_session):
        """Test initial suggestion generation (no session).
        
        Uses mocked suggestion service from conftest (AI + Redis are 3rd party).
        """
        user, profile = test_user_with_profile
        
        payload = {
            "meal_type": "lunch",
            "meal_portion_type": "main",
            "cooking_time_minutes": 20,
            "ingredients": ["chicken", "rice"],
            "language": "en"
        }
        
        # Act: POST generate - uses mocked suggestion service from conftest
        response = authenticated_client.post("/v1/meal-suggestions/generate", json=payload)
        
        # Assert: Returns 3 suggestions + session_id (from real service with mocked AI)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        # Response uses "meal_name" not "name"
        assert data["suggestions"][0]["meal_name"] == "Grilled Chicken Salad"
    
    def test_generate_suggestions_regenerate(self, authenticated_client, test_user_with_profile, test_session):
        """Test regeneration with session_id (excludes previous).
        
        Uses mocked suggestion service from conftest (AI + Redis are 3rd party).
        Note: For regeneration, we need to create a session first, then regenerate.
        """
        user, profile = test_user_with_profile
        
        # First, create an initial session
        initial_payload = {
            "meal_type": "lunch",
            "meal_portion_type": "main",
            "cooking_time_minutes": 20,
            "ingredients": ["chicken", "rice"],
            "language": "en"
        }
        initial_response = authenticated_client.post("/v1/meal-suggestions/generate", json=initial_payload)
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        session_id = initial_data["session_id"]
        
        # Now regenerate with that session_id
        payload = {
            "meal_type": "lunch",
            "meal_portion_type": "main",
            "cooking_time_minutes": 20,
            "session_id": session_id,
            "ingredients": ["chicken", "rice"],
            "language": "en"
        }
        
        # Act: POST with session_id - uses mocked suggestion service from conftest
        response = authenticated_client.post("/v1/meal-suggestions/generate", json=payload)
        
        # Assert: Returns suggestions (from conftest mock)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["suggestions"]) == 3
    
    def test_generate_suggestions_with_ingredients(self, authenticated_client, test_user_with_profile):
        """Test suggestions with ingredient constraints.
        
        Uses mocked suggestion service from conftest (AI + Redis are 3rd party).
        """
        user, profile = test_user_with_profile
        
        payload = {
            "meal_type": "dinner",
            "meal_portion_type": "main",
            "cooking_time_minutes": 30,
            "ingredients": ["chicken", "rice", "broccoli"],
            "language": "en"
        }
        
        # Act: POST with ingredients - uses mocked suggestion service from conftest
        response = authenticated_client.post("/v1/meal-suggestions/generate", json=payload)
        
        # Assert: Returns suggestions (from conftest mock)
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) == 3
    
    # POST /v1/meal-suggestions/save
    def test_save_suggestion_to_meal(self, authenticated_client, test_user, test_session):
        """Test converting suggestion to actual meal.
        
        Uses real handlers (Redis is mocked in conftest).
        """
        payload = {
            "suggestion_id": "suggestion-1",
            "name": "Grilled Chicken Salad",
            "meal_type": "lunch",
            "calories": 450,
            "protein": 35.0,
            "carbs": 30.0,
            "fat": 20.0,
            "description": "Healthy grilled chicken salad",
            "estimated_cook_time_minutes": 20,
            "ingredients_list": ["Chicken", "Lettuce", "Tomato"],
            "instructions": ["Grill chicken", "Serve over salad"],
            "portion_multiplier": 1,
            "meal_date": "2024-12-25"
        }
        
        # Act: POST save - uses real handler
        response = authenticated_client.post("/v1/meal-suggestions/save", json=payload)
        
        # Assert: Meal created from suggestion (real handler response)
        assert response.status_code == 200
        data = response.json()
        assert "planned_meal_id" in data or "meal_id" in data
        assert "message" in data or "status" in data
        assert data.get("meal_date") == "2024-12-25" or "date" in data
