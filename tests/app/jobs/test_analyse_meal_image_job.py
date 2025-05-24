import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import uuid

from domain.model.meal import Meal, MealStatus
from domain.model.meal_image import MealImage
from domain.services.gpt_response_parser import GPTResponseParser, GPTResponseParsingError
from app.jobs.analyse_meal_image_job import AnalyseMealImageJob

class TestAnalyseMealImageJob:
    """Tests for the AnalyseMealImageJob."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.meal_repository = Mock()
        self.image_store = Mock()
        self.vision_service = Mock()
        self.gpt_parser = Mock()
        
        # Create the job with mocked dependencies
        self.job = AnalyseMealImageJob(
            meal_repository=self.meal_repository,
            image_store=self.image_store,
            vision_service=self.vision_service,
            gpt_parser=self.gpt_parser
        )
        
        # Create a test meal
        self.test_image = MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=1000,
            width=100,
            height=100
        )
        
        self.test_meal = Meal(
            meal_id=str(uuid.uuid4()),
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=self.test_image
        )
    
    def test_run_no_meals(self):
        """Test run when there are no meals to process."""
        # Arrange
        self.meal_repository.find_by_status.return_value = []
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 0
        self.meal_repository.find_by_status.assert_called_once_with(
            status=MealStatus.PROCESSING,
            limit=5
        )
    
    def test_process_meal_success(self):
        """Test successful processing of a meal."""
        # Arrange
        self.meal_repository.find_by_status.return_value = [self.test_meal]
        
        # Mock image loading
        self.image_store.load.return_value = b"fake image bytes"
        
        # Mock vision service
        gpt_response = {"raw_response": "GPT response", "structured_data": {"foods": []}}
        self.vision_service.analyze.return_value = gpt_response
        
        # Mock parser
        nutrition = MagicMock()
        self.gpt_parser.parse_to_nutrition.return_value = nutrition
        self.gpt_parser.extract_raw_json.return_value = "raw json"
        
        # Mock meal status transitions
        analyzing_meal = MagicMock()
        self.test_meal.mark_analyzing.return_value = analyzing_meal
        
        enriched_meal = MagicMock()
        analyzing_meal.mark_enriching.return_value = enriched_meal
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 1
        self.meal_repository.save.assert_called_with(enriched_meal)
        self.image_store.load.assert_called_once_with(self.test_image.image_id)
        self.vision_service.analyze.assert_called_once_with(b"fake image bytes")
        self.gpt_parser.parse_to_nutrition.assert_called_once_with(gpt_response)
        analyzing_meal.mark_enriching.assert_called_once_with("raw json")
    
    def test_process_meal_image_load_failure(self):
        """Test handling of image loading failure."""
        # Arrange
        self.meal_repository.find_by_status.return_value = [self.test_meal]
        
        # Mock image loading failure
        self.image_store.load.return_value = None
        
        # Mock meal status transitions
        analyzing_meal = MagicMock()
        self.test_meal.mark_analyzing.return_value = analyzing_meal
        
        failed_meal = MagicMock()
        analyzing_meal.mark_failed.return_value = failed_meal
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 0
        self.meal_repository.save.assert_called_with(failed_meal)
    
    def test_process_meal_parsing_failure(self):
        """Test handling of GPT response parsing failure."""
        # Arrange
        self.meal_repository.find_by_status.return_value = [self.test_meal]
        
        # Mock image loading
        self.image_store.load.return_value = b"fake image bytes"
        
        # Mock vision service
        gpt_response = {"raw_response": "Invalid GPT response"}
        self.vision_service.analyze.return_value = gpt_response
        
        # Mock parser failure
        self.gpt_parser.parse_to_nutrition.side_effect = GPTResponseParsingError("Parsing error")
        
        # Mock meal status transitions
        analyzing_meal = MagicMock()
        self.test_meal.mark_analyzing.return_value = analyzing_meal
        
        failed_meal = MagicMock()
        analyzing_meal.mark_failed.return_value = failed_meal
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 0
        analyzing_meal.mark_failed.assert_called_once()
        self.meal_repository.save.assert_called_with(failed_meal) 