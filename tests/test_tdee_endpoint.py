from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_tdee_calculation_with_body_fat_metric():
    """Test TDEE calculation with body fat percentage (Katch-McArdle formula) using metric units."""
    payload = {
        "age": 30,
        "sex": "male",
        "height": 180,  # cm
        "weight": 80,   # kg
        "body_fat_percentage": 15,
        "activity_level": "moderate",
        "goal": "maintenance",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure matches Flutter TdeeResult
    assert "bmr" in data
    assert "tdee" in data
    assert "maintenance" in data
    assert "cutting" in data
    assert "bulking" in data
    
    # Check macro structure matches Flutter MacroTargets
    for goal in ["maintenance", "cutting", "bulking"]:
        assert "calories" in data[goal]
        assert "protein" in data[goal]
        assert "fat" in data[goal]
        assert "carbs" in data[goal]
    
    # Verify calculations are reasonable
    assert data["bmr"] > 0
    assert data["tdee"] > data["bmr"]
    assert data["cutting"]["calories"] < data["maintenance"]["calories"] < data["bulking"]["calories"]


def test_tdee_calculation_without_body_fat_imperial():
    """Test TDEE calculation without body fat percentage using imperial units."""
    payload = {
        "age": 25,
        "sex": "female",
        "height": 65,    # inches
        "weight": 130,   # lbs
        "body_fat_percentage": None,
        "activity_level": "light",
        "goal": "cutting",
        "unit_system": "imperial"
    }
    
    response = client.post("/v1/tdee", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure matches Flutter TdeeResult
    assert "bmr" in data
    assert "tdee" in data
    assert "maintenance" in data
    assert "cutting" in data
    assert "bulking" in data


def test_tdee_with_active_activity_level():
    """Test TDEE calculation with 'active' activity level (matches Flutter enum)."""
    payload = {
        "age": 28,
        "sex": "male",
        "height": 175,
        "weight": 75,
        "body_fat_percentage": None,
        "activity_level": "active",  # Changed from 'very' to 'active'
        "goal": "bulking",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "bmr" in data
    assert "tdee" in data
    assert data["tdee"] > data["bmr"]


def test_tdee_validation_errors():
    """Test validation errors for invalid input."""
    # Test invalid age
    payload = {
        "age": 150,  # Too high
        "sex": "male",
        "height": 180,
        "weight": 80,
        "activity_level": "moderate",
        "goal": "maintenance",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    assert response.status_code == 422  # Pydantic validation error
    
    # Test invalid activity level
    payload = {
        "age": 30,
        "sex": "male", 
        "height": 180,
        "weight": 80,
        "activity_level": "invalid",
        "goal": "maintenance",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    assert response.status_code == 422
    
    # Test invalid goal
    payload = {
        "age": 30,
        "sex": "male",
        "height": 180,
        "weight": 80,
        "activity_level": "moderate",
        "goal": "invalid",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    assert response.status_code == 422


def test_unit_conversion_validation():
    """Test unit system validation."""
    # Test invalid height for metric
    payload = {
        "age": 30,
        "sex": "male",
        "height": 50,  # Too low for metric (should be 100-272 cm)
        "weight": 80,
        "activity_level": "moderate",
        "goal": "maintenance",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    assert response.status_code == 422
    
    # Test valid height for imperial
    payload = {
        "age": 30,
        "sex": "male",
        "height": 70,  # Valid for imperial (39-107 inches)
        "weight": 170, # Valid for imperial (66-551 lbs)
        "activity_level": "moderate", 
        "goal": "maintenance",
        "unit_system": "imperial"
    }
    
    response = client.post("/v1/tdee", json=payload)
    assert response.status_code == 200


def test_flutter_enum_compatibility():
    """Test that all Flutter enum values are supported."""
    # Test all activity levels
    activity_levels = ["sedentary", "light", "moderate", "active", "extra"]
    for activity in activity_levels:
        payload = {
            "age": 30,
            "sex": "male",
            "height": 180,
            "weight": 80,
            "activity_level": activity,
            "goal": "maintenance",
            "unit_system": "metric"
        }
        
        response = client.post("/v1/tdee", json=payload)
        assert response.status_code == 200, f"Failed for activity level: {activity}"
    
    # Test all goals
    goals = ["maintenance", "cutting", "bulking"]
    for goal in goals:
        payload = {
            "age": 30,
            "sex": "male",
            "height": 180,
            "weight": 80,
            "activity_level": "moderate",
            "goal": goal,
            "unit_system": "metric"
        }
        
        response = client.post("/v1/tdee", json=payload)
        assert response.status_code == 200, f"Failed for goal: {goal}"


def test_response_format_matches_flutter():
    """Test that response format exactly matches Flutter TdeeResult expectations."""
    payload = {
        "age": 30,
        "sex": "male",
        "height": 180,
        "weight": 80,
        "body_fat_percentage": None,
        "activity_level": "moderate",
        "goal": "cutting",
        "unit_system": "metric"
    }
    
    response = client.post("/v1/tdee", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify exact structure matches Flutter TdeeResult
    assert isinstance(data["bmr"], (int, float))
    assert isinstance(data["tdee"], (int, float))
    
    # Verify MacroTargets structure
    for goal_name in ["maintenance", "cutting", "bulking"]:
        macro_targets = data[goal_name]
        assert isinstance(macro_targets["calories"], (int, float))
        assert isinstance(macro_targets["protein"], (int, float))
        assert isinstance(macro_targets["fat"], (int, float))
        assert isinstance(macro_targets["carbs"], (int, float))
        
        # All values should be positive
        assert macro_targets["calories"] > 0
        assert macro_targets["protein"] > 0
        assert macro_targets["fat"] > 0
        assert macro_targets["carbs"] > 0 