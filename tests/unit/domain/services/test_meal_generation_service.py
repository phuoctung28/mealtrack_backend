"""
Unit tests for MealGenerationService.
"""
import pytest
from unittest.mock import Mock, patch
from pydantic import BaseModel, Field
from typing import List

from src.infra.adapters.meal_generation_service import MealGenerationService


class MockMealNamesResponse(BaseModel):
    """Mock schema for testing structured output."""
    meal_names: List[str] = Field(description="List of meal names")


class TestMealGenerationService:
    """Test suite for MealGenerationService."""

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_api_key'})
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        service = MealGenerationService()
        assert service.api_key == 'test_api_key'
        assert service.base_llm_config is not None
        assert service.base_llm_config['model'] == 'gemini-2.5-flash'
        assert service.base_llm_config['temperature'] == 0.2

    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        service = MealGenerationService()
        assert service.api_key is None
        assert service.llm is None

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_json_response(self, mock_llm_class):
        """Test generating meal plan with JSON response."""
        service = MealGenerationService()
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = '{"meal": "test", "calories": 500}'
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm_instance
        
        result = service.generate_meal_plan(
            prompt="Generate a meal",
            system_message="You are a chef",
            response_type="json"
        )
        
        assert result == {"meal": "test", "calories": 500}
        mock_llm_instance.invoke.assert_called_once()

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_text_response(self, mock_llm_class):
        """Test generating meal plan with text response."""
        service = MealGenerationService()
        
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "Plain text response"
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm_instance
        
        result = service.generate_meal_plan(
            prompt="Generate a meal",
            system_message="You are a chef",
            response_type="text"
        )
        
        assert result == {"raw_content": "Plain text response"}

    @patch.dict('os.environ', {}, clear=True)
    def test_generate_meal_plan_no_api_key(self):
        """Test error when API key is missing."""
        service = MealGenerationService()
        
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY missing"):
            service.generate_meal_plan(
                prompt="Test",
                system_message="Test",
                response_type="json"
            )

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_determine_optimal_tokens_weekly(self):
        """Test token optimization for weekly plans."""
        service = MealGenerationService()
        
        prompt = "Generate a weekly meal plan for 7 days Monday through Sunday"
        system_message = "You are a meal planner"
        
        tokens = service._determine_optimal_tokens(prompt, system_message)
        
        assert tokens == 8000  # High token limit for weekly

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_determine_optimal_tokens_daily_multiple(self):
        """Test token optimization for daily multiple meals."""
        service = MealGenerationService()
        
        prompt = "Generate breakfast, lunch, dinner and snack"
        system_message = "You are a meal planner"
        
        tokens = service._determine_optimal_tokens(prompt, system_message)
        
        assert tokens == 3000  # Medium token limit

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_determine_optimal_tokens_single(self):
        """Test token optimization for single meal."""
        service = MealGenerationService()
        
        prompt = "Generate a single breakfast"
        system_message = "You are a chef"
        
        tokens = service._determine_optimal_tokens(prompt, system_message)
        
        assert tokens == 1500  # Low token limit

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_extract_json_direct_parse(self):
        """Test extracting JSON with direct parsing."""
        service = MealGenerationService()
        
        content = '{"meal": "pasta", "calories": 600}'
        result = service._extract_json(content)
        
        assert result == {"meal": "pasta", "calories": 600}

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        service = MealGenerationService()
        
        content = '''Here is the meal plan:
```json
{"meal": "salad", "calories": 300}
```
Enjoy!'''
        
        result = service._extract_json(content)
        
        assert result == {"meal": "salad", "calories": 300}

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_extract_json_with_trailing_comma(self):
        """Test extracting JSON with trailing commas."""
        service = MealGenerationService()
        
        content = '{"meal": "soup", "calories": 400,}'
        result = service._extract_json(content)
        
        assert result == {"meal": "soup", "calories": 400}

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_extract_json_invalid(self):
        """Test error when JSON cannot be extracted."""
        service = MealGenerationService()
        
        content = "This is not JSON at all"
        
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            service._extract_json(content)

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_clean_json_content_trailing_commas(self):
        """Test cleaning JSON content with trailing commas."""
        service = MealGenerationService()
        
        content = '{"name": "meal", "items": ["a", "b",],}'
        cleaned = service._clean_json_content(content)
        
        # Should remove trailing commas
        assert ",]" not in cleaned
        assert ",}" not in cleaned

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_clean_json_content_extra_text(self):
        """Test cleaning JSON content with extra text after."""
        service = MealGenerationService()
        
        content = '{"name": "meal"} extra text here'
        cleaned = service._clean_json_content(content)
        
        # Should stop at the closing brace
        assert cleaned == '{"name": "meal"}'

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_clean_json_content_empty(self):
        """Test cleaning empty content."""
        service = MealGenerationService()
        
        result = service._clean_json_content("")
        assert result == ""

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_with_custom_tokens(self, mock_llm_class):
        """Test generating meal plan with custom max tokens."""
        service = MealGenerationService()
        
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = '{"test": "data"}'
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm_instance
        
        service.generate_meal_plan(
            prompt="Test",
            system_message="Test",
            response_type="json",
            max_tokens=5000
        )
        
        # Verify LLM was created with custom tokens
        mock_llm_class.assert_called_once()
        call_kwargs = mock_llm_class.call_args[1]
        assert call_kwargs['max_output_tokens'] == 5000

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_llm_error(self, mock_llm_class):
        """Test handling LLM errors."""
        service = MealGenerationService()
        
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.side_effect = Exception("LLM API error")
        mock_llm_class.return_value = mock_llm_instance
        
        with pytest.raises(Exception, match="LLM API error"):
            service.generate_meal_plan(
                prompt="Test",
                system_message="Test",
                response_type="json"
            )

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_extract_json_nested_objects(self):
        """Test extracting complex nested JSON."""
        service = MealGenerationService()
        
        content = '''
        {
            "days": {
                "monday": {
                    "meals": [
                        {"name": "breakfast", "calories": 400},
                        {"name": "lunch", "calories": 600}
                    ]
                }
            }
        }
        '''
        
        result = service._extract_json(content)
        
        assert "days" in result
        assert "monday" in result["days"]
        assert len(result["days"]["monday"]["meals"]) == 2

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_determine_optimal_tokens_case_insensitive(self):
        """Test token optimization is case insensitive."""
        service = MealGenerationService()
        
        prompt_upper = "Generate meals for MONDAY, TUESDAY, WEDNESDAY"
        prompt_lower = "generate meals for monday, tuesday, wednesday"
        
        tokens_upper = service._determine_optimal_tokens(prompt_upper, "")
        tokens_lower = service._determine_optimal_tokens(prompt_lower, "")
        
        assert tokens_upper == tokens_lower

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_clean_json_content_unmatched_braces(self):
        """Test cleaning JSON with unmatched braces."""
        service = MealGenerationService()

        content = '{"name": "test", "data": {"nested": "value"'
        cleaned = service._clean_json_content(content)

        # Should handle gracefully
        assert "{" in cleaned
        assert "name" in cleaned

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_with_structured_output(self, mock_llm_class):
        """Test generating meal plan with structured output schema."""
        service = MealGenerationService()

        # Mock LLM with structured output
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()

        # Create a mock Pydantic model response
        mock_parsed = MockMealNamesResponse(meal_names=["Meal 1", "Meal 2", "Meal 3"])
        mock_response = {
            "parsed": mock_parsed,
            "raw": Mock(content='{"meal_names": ["Meal 1", "Meal 2", "Meal 3"]}')
        }
        mock_structured_llm.invoke.return_value = mock_response
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        result = service.generate_meal_plan(
            prompt="Generate meal names",
            system_message="You are a chef",
            response_type="json",
            schema=MockMealNamesResponse
        )

        assert result == {"meal_names": ["Meal 1", "Meal 2", "Meal 3"]}
        mock_llm_instance.with_structured_output.assert_called_once()

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_structured_output_none_with_raw_fallback(self, mock_llm_class):
        """Test structured output falls back to raw JSON when parsed is None."""
        service = MealGenerationService()

        mock_llm_instance = Mock()
        mock_structured_llm = Mock()

        # Structured output fails (None), but raw response has valid JSON
        mock_response = {
            "parsed": None,
            "raw": Mock(content='{"meal_names": ["Fallback Meal"]}')
        }
        mock_structured_llm.invoke.return_value = mock_response
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        result = service.generate_meal_plan(
            prompt="Generate meal names",
            system_message="You are a chef",
            response_type="json",
            schema=MockMealNamesResponse
        )

        # Should fall back to parsing raw content
        assert result == {"meal_names": ["Fallback Meal"]}

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_structured_output_none_raises_error(self, mock_llm_class):
        """Test structured output raises error when both parsed and raw fail."""
        service = MealGenerationService()

        mock_llm_instance = Mock()
        mock_structured_llm = Mock()

        # Both parsed and raw fail
        mock_response = {
            "parsed": None,
            "raw": Mock(content='invalid json content')
        }
        mock_structured_llm.invoke.return_value = mock_response
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        with pytest.raises(ValueError, match="Structured output returned None"):
            service.generate_meal_plan(
                prompt="Generate meal names",
                system_message="You are a chef",
                response_type="json",
                schema=MockMealNamesResponse
            )

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_no_schema_uses_legacy_json(self, mock_llm_class):
        """Test that not providing schema uses legacy JSON mode with response_mime_type."""
        service = MealGenerationService()

        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = '{"meal": "test"}'
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm_instance

        service.generate_meal_plan(
            prompt="Generate a meal",
            system_message="You are a chef",
            response_type="json"
            # No schema parameter
        )

        # Verify LLM was created with response_mime_type (legacy mode)
        call_kwargs = mock_llm_class.call_args[1]
        assert call_kwargs.get('response_mime_type') == 'application/json'

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    @patch('src.infra.adapters.meal_generation_service.ChatGoogleGenerativeAI')
    def test_generate_meal_plan_with_schema_no_response_mime_type(self, mock_llm_class):
        """Test that providing schema does NOT set response_mime_type (incompatible)."""
        service = MealGenerationService()

        mock_llm_instance = Mock()
        mock_structured_llm = Mock()

        mock_parsed = MockMealNamesResponse(meal_names=["Meal"])
        mock_response = {"parsed": mock_parsed, "raw": None}
        mock_structured_llm.invoke.return_value = mock_response
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        service.generate_meal_plan(
            prompt="Generate a meal",
            system_message="You are a chef",
            response_type="json",
            schema=MockMealNamesResponse
        )

        # Verify LLM was NOT created with response_mime_type (incompatible with structured output)
        call_kwargs = mock_llm_class.call_args[1]
        assert 'response_mime_type' not in call_kwargs

