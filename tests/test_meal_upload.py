import os
import sys
import json
import pytest
from fastapi.testclient import TestClient
from io import BytesIO
import requests

# Add the root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app

# Create test client
client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_meal_image_upload():
    """Test uploading a meal image."""
    # Path to test image
    image_path = "tests/test_image.jpg"
    
    # Create test image if it doesn't exist
    if not os.path.exists(image_path):
        # Download a sample image
        try:
            image_url = "https://via.placeholder.com/800x600.jpg"  # Placeholder image
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Save the image
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            pytest.skip(f"Failed to download test image: {str(e)}")
    
    # Open the image file
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Upload the image
    response = client.post(
        "/v1/meals/image",
        files={"file": ("test_image.jpg", image_data, "image/jpeg")}
    )
    
    # Check the response
    assert response.status_code == 201, f"Response: {response.text}"
    response_data = response.json()
    
    # Validate response structure
    assert "meal_id" in response_data
    assert "status" in response_data
    assert response_data["status"] == "PROCESSING"
    
    # Store meal_id for future tests
    meal_id = response_data["meal_id"]
    
    # Test getting meal status
    status_response = client.get(f"/v1/meals/{meal_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    assert status_data["meal_id"] == meal_id
    assert status_data["status"] == "PROCESSING"
    assert "status_message" in status_data

if __name__ == "__main__":
    # Run tests directly if script is executed
    test_health_check()
    test_meal_image_upload()
    print("All tests passed!") 