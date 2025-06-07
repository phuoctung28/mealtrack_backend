import json

import pytest

from domain.model.nutrition import Nutrition
from domain.services.gpt_response_parser import GPTResponseParser, GPTResponseParsingError


class TestGPTResponseParser:
    """Tests for the GPTResponseParser domain service."""
    
    def test_parse_valid_response(self):
        """Test parsing a valid GPT response."""
        # Arrange
        parser = GPTResponseParser()
        gpt_response = {
            "raw_response": "JSON response from GPT",
            "structured_data": {
                "foods": [
                    {
                        "name": "Grilled Chicken Breast",
                        "quantity": 150.0,
                        "unit": "g",
                        "calories": 250,
                        "macros": {
                            "protein": 45,
                            "carbs": 0,
                            "fat": 7,
                            "fiber": 0
                        }
                    },
                    {
                        "name": "Brown Rice",
                        "quantity": 100.0,
                        "unit": "g",
                        "calories": 120,
                        "macros": {
                            "protein": 3,
                            "carbs": 25,
                            "fat": 1,
                            "fiber": 2
                        }
                    }
                ],
                "total_calories": 370,
                "confidence": 0.85
            }
        }
        
        # Act
        nutrition = parser.parse_to_nutrition(gpt_response)
        
        # Assert
        assert isinstance(nutrition, Nutrition)
        assert nutrition.calories == 370
        assert nutrition.confidence_score == 0.85
        assert len(nutrition.food_items) == 2
        assert nutrition.food_items[0].name == "Grilled Chicken Breast"
        assert nutrition.food_items[1].name == "Brown Rice"
        assert nutrition.macros.protein == 48  # 45 + 3
        assert nutrition.macros.carbs == 25    # 0 + 25
        assert nutrition.macros.fat == 8       # 7 + 1
        assert nutrition.macros.fiber == 2     # 0 + 2
    
    def test_parse_missing_structured_data(self):
        """Test parsing a response with missing structured data."""
        # Arrange
        parser = GPTResponseParser()
        gpt_response = {
            "raw_response": "Some text without structured data"
        }
        
        # Act & Assert
        with pytest.raises(GPTResponseParsingError):
            parser.parse_to_nutrition(gpt_response)
    
    def test_parse_missing_required_fields(self):
        """Test parsing a response with missing required fields in food items."""
        # Arrange
        parser = GPTResponseParser()
        gpt_response = {
            "structured_data": {
                "foods": [
                    {
                        "name": "Incomplete Food",
                        "quantity": 100.0,
                        # Missing unit, calories, and macros
                    }
                ],
                "confidence": 0.5
            }
        }
        
        # Act & Assert
        with pytest.raises(GPTResponseParsingError):
            parser.parse_to_nutrition(gpt_response)
    
    def test_extract_raw_json(self):
        """Test extracting raw JSON from response."""
        # Arrange
        parser = GPTResponseParser()
        raw_text = "This is the raw GPT response"
        gpt_response = {
            "raw_response": raw_text,
            "structured_data": {"some": "data"}
        }
        
        # Act
        result = parser.extract_raw_json(gpt_response)
        
        # Assert
        assert result == raw_text
        
    def test_extract_raw_json_fallback(self):
        """Test extracting raw JSON falls back to structured data if raw_response is missing."""
        # Arrange
        parser = GPTResponseParser()
        structured_data = {"foods": [], "confidence": 0.5}
        gpt_response = {
            "structured_data": structured_data
        }
        
        # Act
        result = parser.extract_raw_json(gpt_response)
        
        # Assert
        assert json.loads(result) == structured_data 