import pytest
from unittest.mock import patch, MagicMock
import json
import base64
import os

from domain.ports.vision_ai_service_port import VisionAIServicePort
from infra.adapters.vision_ai_service import VisionAIService

class TestVisionAIService:
    """Tests for the Vision AI service adapter."""
    
    @pytest.fixture
    def mock_env_vars(self):
        """Set up mock environment variables."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_api_key"}):
            yield
    
    @pytest.fixture
    def mock_chat_genai(self):
        """Mock the ChatGoogleGenerativeAI class."""
        with patch("infra.adapters.vision_ai_service.ChatGoogleGenerativeAI") as mock:
            # Set up the mock response
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "foods": [
                    {
                        "name": "Test Food",
                        "quantity": 100,
                        "unit": "g",
                        "calories": 200,
                        "macros": {
                            "protein": 20,
                            "carbs": 10,
                            "fat": 5
                        }
                    }
                ],
                "total_calories": 200,
                "confidence": 0.8
            })
            mock_instance.invoke.return_value = mock_response
            mock.return_value = mock_instance
            yield mock
    
    def test_initialization(self, mock_env_vars):
        """Test service initialization with API key."""
        # Act
        service = VisionAIService()
        
        # Assert
        assert service.api_key == "test_api_key"
    
    def test_initialization_no_api_key(self):
        """Test service initialization fails without API key."""
        # Act & Assert
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                VisionAIService()
    
    def test_analyze_image(self, mock_env_vars, mock_chat_genai):
        """Test analyzing an image."""
        # Arrange
        service = VisionAIService()
        image_bytes = b"fake image data"
        
        # Act
        result = service.analyze(image_bytes)
        
        # Assert
        assert "raw_response" in result
        assert "structured_data" in result
        assert result["structured_data"]["foods"][0]["name"] == "Test Food"
        assert result["structured_data"]["confidence"] == 0.8
        
        # Verify the correct message was sent
        mock_chat_genai.return_value.invoke.assert_called_once()
        call_args = mock_chat_genai.return_value.invoke.call_args[0][0]
        
        # Check that the image was encoded correctly
        image_message = call_args[1].content[1]
        assert image_message["type"] == "image_url"
        assert "data:image/jpeg;base64," in image_message["image_url"]["url"]
        
    def test_analyze_error_handling(self, mock_env_vars, mock_chat_genai):
        """Test error handling during analysis."""
        # Arrange
        service = VisionAIService()
        mock_chat_genai.return_value.invoke.side_effect = Exception("API error")
        
        # Act & Assert
        with pytest.raises(RuntimeError):
            service.analyze(b"fake image data")
    
    def test_json_extraction_from_markdown(self, mock_env_vars):
        """Test extracting JSON from markdown code blocks."""
        # Arrange
        service = VisionAIService()
        mock_response = MagicMock()
        mock_response.content = """
        Here's the analysis:
        
        ```json
        {
          "foods": [{"name": "Test Food", "quantity": 100, "unit": "g", "calories": 200, "macros": {"protein": 20, "carbs": 10, "fat": 5}}],
          "total_calories": 200,
          "confidence": 0.8
        }
        ```
        """
        
        with patch("infra.adapters.vision_ai_service.ChatGoogleGenerativeAI") as mock:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock.return_value = mock_instance
            
            # Act
            result = service.analyze(b"fake image data")
            
            # Assert
            assert result["structured_data"]["foods"][0]["name"] == "Test Food"
            assert result["structured_data"]["confidence"] == 0.8 