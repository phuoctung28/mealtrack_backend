import pytest
import httpx
import os
from typing import Dict, Any

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")


class TestMealPlanningConversation:
    """Test the conversational meal planning feature"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    def test_start_conversation(self, client):
        """Test starting a new meal planning conversation"""
        response = client.post("/v1/meal-plans/conversations/start?user_id=test_user")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversation_id" in data
        assert "state" in data
        assert "assistant_message" in data
        assert data["state"] == "asking_dietary_preferences"
        assert "dietary preferences" in data["assistant_message"].lower()
    
    def test_complete_conversation_flow(self, client):
        """Test a complete conversation flow"""
        # Start conversation
        start_response = client.post("/v1/meal-plans/conversations/start?user_id=test_user")
        assert start_response.status_code == 200
        conversation_id = start_response.json()["conversation_id"]
        
        # Answer dietary preferences
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "I'm gluten-free and prefer vegetarian meals"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_allergies"
        
        # Answer allergies
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "No allergies"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_fitness_goals"
        
        # Answer fitness goals
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "I'm trying to gain muscle"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_meal_count"
        
        # Answer meal count
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "3 meals and 2 snacks"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_plan_duration"
        
        # Answer plan duration
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "I'd like a weekly plan"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_cooking_time"
        
        # Answer cooking time
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "30 minutes on weekdays, more on weekends"}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "asking_cuisine_preferences"
        
        # Answer cuisine preferences
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "I love Italian food and spicy dishes. I don't like tofu."}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "confirming_preferences"
        
        # Confirm preferences
        response = client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "Yes, that sounds perfect!"}
        )
        # This should generate the meal plan
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "showing_plan"
        assert "meal_plan_id" in data
        assert data["meal_plan_id"] is not None
    
    def test_get_conversation_history(self, client):
        """Test retrieving conversation history"""
        # Start a conversation first
        start_response = client.post("/v1/meal-plans/conversations/start?user_id=test_user")
        conversation_id = start_response.json()["conversation_id"]
        
        # Send a message
        client.post(
            f"/v1/meal-plans/conversations/{conversation_id}/messages",
            json={"message": "I'm vegan"}
        )
        
        # Get conversation history
        response = client.get(f"/v1/meal-plans/conversations/{conversation_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
        assert len(data["messages"]) >= 2  # At least greeting and user message
        assert "context" in data


class TestDirectMealPlanGeneration:
    """Test direct meal plan generation without conversation"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    def test_generate_meal_plan_directly(self, client):
        """Test generating a meal plan directly with preferences"""
        preferences = {
            "dietary_preferences": ["vegetarian", "gluten_free"],
            "allergies": ["nuts"],
            "fitness_goal": "muscle_gain",
            "meals_per_day": 3,
            "snacks_per_day": 2,
            "cooking_time_weekday": 30,
            "cooking_time_weekend": 60,
            "favorite_cuisines": ["Italian", "Mexican"],
            "disliked_ingredients": ["tofu", "mushrooms"],
            "plan_duration": "weekly"
        }
        
        response = client.post(
            "/v1/meal-plans/generate?user_id=test_user",
            json={"preferences": preferences}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "plan_id" in data
        assert "user_id" in data
        assert data["user_id"] == "test_user"
        assert "days" in data
        assert len(data["days"]) == 7  # Weekly plan
        
        # Check first day
        first_day = data["days"][0]
        assert "date" in first_day
        assert "meals" in first_day
        assert "total_nutrition" in first_day
        
        # Check meals structure
        meals = first_day["meals"]
        assert len(meals) == 5  # 3 meals + 2 snacks
        
        for meal in meals:
            assert "meal_id" in meal
            assert "meal_type" in meal
            assert "name" in meal
            assert "description" in meal
            assert "calories" in meal
            assert "protein" in meal
            assert "is_gluten_free" in meal
            assert meal["is_gluten_free"] == True  # Should respect gluten-free preference
    
    def test_meal_plan_health_check(self, client):
        """Test meal planning service health check"""
        response = client.get("/v1/meal-plans/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "meal_planning"
        assert "features" in data


@pytest.mark.skip(reason="Requires database implementation")
class TestMealPlanPersistence:
    """Test meal plan persistence and retrieval"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    def test_get_saved_meal_plan(self, client):
        """Test retrieving a saved meal plan"""
        # This would require database implementation
        pass
    
    def test_replace_meal_in_plan(self, client):
        """Test replacing a specific meal in a plan"""
        # This would require database implementation
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])