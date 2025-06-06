import pytest
import httpx
import io


@pytest.mark.api
class TestInputValidation:
    """Test input validation for all endpoints."""
    
    def test_food_creation_validation(self, api_client, invalid_data_samples):
        """Test food creation with invalid input data."""
        
        # Test missing required field (name)
        response = api_client.post("/v1/food/", json=invalid_data_samples["food_missing_name"])
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("name" in str(error).lower() for error in error_detail)
        
        # Test negative values
        response = api_client.post("/v1/food/", json=invalid_data_samples["food_negative_values"])
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # Should complain about negative protein
        assert any("protein" in str(error).lower() and "greater" in str(error).lower() for error in error_detail)
    
    def test_onboarding_validation(self, api_client, invalid_data_samples):
        """Test onboarding data validation."""
        
        # Test invalid age
        response = api_client.post("/v1/macros/calculate", json=invalid_data_samples["onboarding_invalid_age"])
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("age" in str(error).lower() for error in error_detail)
        
        # Test invalid gender
        response = api_client.post("/v1/macros/calculate", json=invalid_data_samples["onboarding_invalid_gender"])
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("gender" in str(error).lower() for error in error_detail)
    
    def test_pagination_validation(self, api_client):
        """Test pagination parameter validation."""
        
        # Test invalid page number (0 or negative)
        response = api_client.get("/v1/food-database/", params={"page": 0})
        assert response.status_code == 422
        
        response = api_client.get("/v1/food-database/", params={"page": -1})
        assert response.status_code == 422
        
        # Test invalid page size (too large)
        response = api_client.get("/v1/food-database/", params={"page_size": 150})
        assert response.status_code == 422
        
        # Test invalid page size (0 or negative)
        response = api_client.get("/v1/food-database/", params={"page_size": 0})
        assert response.status_code == 422
    
    def test_search_validation(self, api_client):
        """Test search parameter validation."""
        
        # Test empty search query
        response = api_client.post("/v1/food-database/search", json={"query": "", "limit": 10})
        assert response.status_code == 422
        
        # Test search query too long
        long_query = "a" * 250  # Exceeds max length of 200
        response = api_client.post("/v1/food-database/search", json={"query": long_query, "limit": 10})
        assert response.status_code == 422
        
        # Test invalid limit (too large)
        response = api_client.post("/v1/food-database/search", json={"query": "chicken", "limit": 150})
        assert response.status_code == 422
        
        # Test invalid limit (0 or negative)
        response = api_client.post("/v1/food-database/search", json={"query": "chicken", "limit": 0})
        assert response.status_code == 422
    
    def test_ingredient_validation(self, api_client):
        """Test ingredient data validation."""
        food_id = "test-food-id"
        
        # Test missing required fields
        incomplete_data = {
            "name": "Test Ingredient"
            # Missing quantity and unit
        }
        response = api_client.post(f"/v1/food/{food_id}/ingredients/", json=incomplete_data)
        assert response.status_code == 422
        
        # Test negative quantity
        invalid_data = {
            "name": "Test Ingredient",
            "quantity": -5.0,  # Negative quantity
            "unit": "g"
        }
        response = api_client.post(f"/v1/food/{food_id}/ingredients/", json=invalid_data)
        assert response.status_code == 422
        
        # Test negative calories
        invalid_data = {
            "name": "Test Ingredient",
            "quantity": 10.0,
            "unit": "g",
            "calories": -50.0  # Negative calories
        }
        response = api_client.post(f"/v1/food/{food_id}/ingredients/", json=invalid_data)
        assert response.status_code == 422
    
    def test_macros_update_validation(self, api_client):
        """Test macros update validation."""
        
        # Test missing both size and amount
        invalid_data = {
            "unit": "g"
            # Missing both size and amount
        }
        food_id = "test-food-id"
        response = api_client.post(f"/v1/food/{food_id}/macros", json=invalid_data)
        assert response.status_code == 422
        
        # Test negative size
        invalid_data = {
            "size": -100.0,  # Negative size
            "unit": "g"
        }
        response = api_client.post(f"/v1/food/{food_id}/macros", json=invalid_data)
        assert response.status_code == 422
    
    def test_consumed_macros_validation(self, api_client):
        """Test consumed macros data validation."""
        
        # Test negative calories
        invalid_data = {
            "calories": -100.0,  # Negative calories
            "macros": {
                "protein": 20.0,
                "carbs": 30.0,
                "fat": 10.0
            }
        }
        response = api_client.post("/v1/macros/consumed", json=invalid_data)
        assert response.status_code == 422
        
        # Test missing macros
        invalid_data = {
            "calories": 100.0
            # Missing required macros field
        }
        response = api_client.post("/v1/macros/consumed", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.api
class TestFileUploadValidation:
    """Test file upload validation for food photo endpoints."""
    
    def test_invalid_file_type(self, api_client):
        """Test uploading invalid file types."""
        # Test text file
        text_data = b"This is not an image"
        files = {"file": ("test.txt", io.BytesIO(text_data), "text/plain")}
        
        response = api_client.post("/v1/food/photo", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
        
        # Test PDF file
        pdf_data = b"%PDF-1.4 fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_data), "application/pdf")}
        
        response = api_client.post("/v1/food/photo", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_oversized_file(self, api_client):
        """Test uploading files that exceed size limit."""
        # Create a file larger than 8MB
        large_file_data = b"x" * (9 * 1024 * 1024)  # 9MB
        files = {"file": ("large_image.jpg", io.BytesIO(large_file_data), "image/jpeg")}
        
        response = api_client.post("/v1/food/photo", files=files)
        assert response.status_code == 400
        assert "File size exceeds maximum" in response.json()["detail"]
    
    def test_missing_file(self, api_client):
        """Test uploading without providing a file."""
        response = api_client.post("/v1/food/photo")
        assert response.status_code == 422  # Missing required field
    
    def test_valid_image_types(self, api_client):
        """Test uploading valid image types."""
        valid_types = [
            ("image.jpg", "image/jpeg"),
            ("image.jpeg", "image/jpeg"),
            ("image.png", "image/png")
        ]
        
        for filename, content_type in valid_types:
            image_data = b"fake_image_data_for_testing"
            files = {"file": (filename, io.BytesIO(image_data), content_type)}
            
            response = api_client.post("/v1/food/photo", files=files)
            assert response.status_code == 201, f"Failed for {content_type}"


@pytest.mark.api
class TestErrorResponseStructure:
    """Test that error responses have consistent structure."""
    
    def test_validation_error_structure(self, api_client):
        """Test validation error response structure."""
        # Trigger a validation error
        response = api_client.post("/v1/food/", json={"brand": "Test"})  # Missing name
        assert response.status_code == 422
        
        error_response = response.json()
        assert "detail" in error_response
        assert isinstance(error_response["detail"], list)
        
        # Each error should have expected structure
        for error in error_response["detail"]:
            assert "loc" in error  # Location of error
            assert "msg" in error  # Error message
            assert "type" in error  # Error type
    
    def test_404_error_structure(self, api_client):
        """Test 404 error response structure."""
        # For now, our endpoints don't return 404s since they use placeholder data
        # This test would be relevant when real database lookups are implemented
        pass
    
    def test_400_error_structure(self, api_client):
        """Test 400 error response structure."""
        # Trigger a 400 error with invalid file upload
        files = {"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")}
        response = api_client.post("/v1/food/photo", files=files)
        assert response.status_code == 400
        
        error_response = response.json()
        assert "detail" in error_response
        assert isinstance(error_response["detail"], str)


@pytest.mark.api
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_extremely_long_strings(self, api_client):
        """Test handling of extremely long string inputs."""
        # Test very long food name
        long_name = "a" * 250  # Exceeds max length of 200
        food_data = {
            "name": long_name,
            "brand": "Test Brand"
        }
        response = api_client.post("/v1/food/", json=food_data)
        assert response.status_code == 422
        
        # Test very long description
        long_description = "a" * 600  # Exceeds max length of 500
        food_data = {
            "name": "Test Food",
            "description": long_description
        }
        response = api_client.post("/v1/food/", json=food_data)
        assert response.status_code == 422
    
    def test_boundary_values(self, api_client):
        """Test boundary values for numeric fields."""
        # Test minimum valid age
        valid_data = {
            "age": 13,  # Minimum allowed age
            "gender": "male",
            "height": 100.0,  # Minimum height
            "weight": 30.0,    # Minimum weight
            "activity_level": "sedentary",
            "goal": "maintain_weight"
        }
        response = api_client.post("/v1/macros/calculate", json=valid_data)
        assert response.status_code == 201
        
        # Test maximum valid age
        valid_data["age"] = 120  # Maximum allowed age
        response = api_client.post("/v1/macros/calculate", json=valid_data)
        assert response.status_code == 201
        
        # Test just over the boundary
        invalid_data = valid_data.copy()
        invalid_data["age"] = 121  # Over maximum
        response = api_client.post("/v1/macros/calculate", json=invalid_data)
        assert response.status_code == 422
    
    def test_zero_values(self, api_client):
        """Test handling of zero values where not allowed."""
        # Test zero serving size (should be positive)
        food_data = {
            "name": "Test Food",
            "serving_size": 0.0  # Zero serving size
        }
        response = api_client.post("/v1/food/", json=food_data)
        assert response.status_code == 422
        
        # Test zero macros (should be allowed)
        food_data = {
            "name": "Test Food",
            "macros_per_serving": {
                "protein": 0.0,  # Zero protein should be allowed
                "carbs": 0.0,
                "fat": 0.0
            }
        }
        response = api_client.post("/v1/food/", json=food_data)
        assert response.status_code == 201
    
    def test_special_characters(self, api_client):
        """Test handling of special characters in inputs."""
        # Test special characters in food name
        special_chars_data = {
            "name": "Test Food with émojis 🍎 and spëcial chars!",
            "brand": "Brand with & symbols",
            "description": "Description with\nnewlines and\ttabs"
        }
        response = api_client.post("/v1/food/", json=special_chars_data)
        assert response.status_code == 201
        
        # Test unicode characters
        unicode_data = {
            "name": "测试食品",  # Chinese characters
            "brand": "Ñew Brand",  # Accented characters
            "description": "Café with açaí"  # Mixed accents
        }
        response = api_client.post("/v1/food/", json=unicode_data)
        assert response.status_code == 201
    
    def test_null_and_empty_values(self, api_client):
        """Test handling of null and empty values."""
        # Test explicit null values for optional fields
        food_data = {
            "name": "Test Food",
            "brand": None,
            "description": None,
            "serving_size": None
        }
        response = api_client.post("/v1/food/", json=food_data)
        assert response.status_code == 201
        
        # Test empty strings for optional fields
        food_data = {
            "name": "Test Food",
            "brand": "",
            "description": ""
        }
        response = api_client.post("/v1/food/", json=food_data)
        # Empty strings might be allowed or rejected depending on validation rules
        # The actual behavior depends on the implementation
        assert response.status_code in [201, 422]


@pytest.mark.api
class TestConcurrentValidation:
    """Test validation under concurrent requests."""
    
    def test_concurrent_invalid_requests(self, base_url):
        """Test that validation works correctly under concurrent load."""
        import concurrent.futures
        
        def make_invalid_request():
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                # Send invalid data (missing required name field)
                response = client.post("/v1/food/", json={"brand": "Test"})
                return response.status_code == 422
        
        # Run multiple invalid requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_invalid_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should be properly validated and rejected
        assert all(results), "All invalid requests should be rejected with 422"


if __name__ == "__main__":
    # Run validation tests with: python -m pytest tests/test_validation.py -v
    pytest.main([__file__, "-v"]) 