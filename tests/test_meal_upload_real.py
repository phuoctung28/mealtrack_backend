import os
import sys
import requests
import tempfile
from io import BytesIO

# Add the root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from api.main import app

# Create test client
client = TestClient(app)

def get_test_image_path():
    """Get the path to the test image."""
    test_image_path = "tests/test_data/noodle_soup.jpg"
    
    # Check if image exists
    if not os.path.exists(test_image_path):
        # Try to download the image
        try:
            # Run the download script
            from tests.download_test_image import download_image
            download_image()
        except Exception as e:
            print(f"Failed to download test image: {e}")
            
            # If still doesn't exist, use a placeholder
            if not os.path.exists(test_image_path):
                print("Using placeholder image instead")
                placeholder_url = "https://via.placeholder.com/800x600.jpg"
                try:
                    response = requests.get(placeholder_url)
                    response.raise_for_status()
                    
                    # Save the placeholder image
                    os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
                    with open(test_image_path, "wb") as f:
                        f.write(response.content)
                    print(f"Saved placeholder image to {test_image_path}")
                except Exception as e:
                    print(f"Failed to save placeholder image: {e}")
                    return None
    
    return test_image_path

def test_upload_noodle_soup_image():
    """Test uploading the Vietnamese noodle soup image."""
    # Get the test image path
    test_image_path = get_test_image_path()
    if not test_image_path or not os.path.exists(test_image_path):
        print("Test image not available, skipping test")
        return
    
    print(f"Using test image: {test_image_path}")
    
    # Open the image file
    with open(test_image_path, "rb") as f:
        image_data = f.read()
    
    # Upload the image
    response = client.post(
        "/v1/meals/image",
        files={"file": ("noodle_soup.jpg", image_data, "image/jpeg")}
    )
    
    # Check the response
    assert response.status_code == 201, f"Response status code: {response.status_code}, body: {response.text}"
    response_data = response.json()
    
    # Validate response structure
    assert "meal_id" in response_data, f"Response doesn't contain meal_id: {response_data}"
    assert "status" in response_data, f"Response doesn't contain status: {response_data}"
    assert response_data["status"] == "PROCESSING", f"Unexpected status: {response_data['status']}"
    
    # Store meal_id for future tests
    meal_id = response_data["meal_id"]
    print(f"Successfully created meal with ID: {meal_id}")
    
    # Test getting meal status
    status_response = client.get(f"/v1/meals/{meal_id}/status")
    assert status_response.status_code == 200, f"Status response code: {status_response.status_code}, body: {status_response.text}"
    status_data = status_response.json()
    
    assert status_data["meal_id"] == meal_id
    assert status_data["status"] == "PROCESSING"
    assert "status_message" in status_data
    
    print(f"Meal status: {status_data['status']}, message: {status_data['status_message']}")
    print("Test completed successfully!")
    return meal_id

def test_get_meal_details():
    """Test getting detailed meal information."""
    # First upload an image
    meal_id = test_upload_noodle_soup_image()
    if not meal_id:
        print("Skipping meal details test as upload failed")
        return
    
    # Get the meal details
    response = client.get(f"/v1/meals/{meal_id}")
    assert response.status_code == 200, f"Response status code: {response.status_code}, body: {response.text}"
    
    # Validate response structure
    meal_data = response.json()
    assert meal_data["meal_id"] == meal_id
    assert meal_data["status"] == "PROCESSING"
    assert "image" in meal_data
    
    print(f"Retrieved meal details successfully: {meal_id}")
    return meal_data

if __name__ == "__main__":
    # Run test directly if script is executed
    print("Running meal image upload test...")
    meal_id = test_upload_noodle_soup_image()
    
    if meal_id:
        print("\nRunning meal details test...")
        meal_data = test_get_meal_details()
        print(f"\nAll tests passed! Meal ID: {meal_id}")
    else:
        print("\nUpload test failed or skipped.") 