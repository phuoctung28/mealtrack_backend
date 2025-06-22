import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.jobs.analyse_meal_image_job import AnalyseMealImageJob
from domain.model.meal import Meal, MealStatus
from domain.model.meal_image import MealImage
from domain.services.gpt_response_parser import GPTResponseParsingError


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
        
        # Create a mock meal with mock image
        self.test_image = MagicMock()
        self.test_image.image_id = str(uuid.uuid4())
        self.test_image.format = "jpeg"
        self.test_image.size_bytes = 1000
        self.test_image.width = 100
        self.test_image.height = 100
        
        self.test_meal = MagicMock()
        self.test_meal.meal_id = str(uuid.uuid4())
        self.test_meal.status = MealStatus.PROCESSING
        self.test_meal.created_at = datetime.now()
        self.test_meal.image = self.test_image
    
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
        
        # Mock meal status transitions - actual flow is: mark_analyzing -> mark_ready -> mark_enriching
        analyzing_meal = MagicMock()
        self.test_meal.mark_analyzing.return_value = analyzing_meal
        
        ready_meal = MagicMock()
        analyzing_meal.mark_ready.return_value = ready_meal
        
        enriched_meal = MagicMock()
        ready_meal.mark_enriching.return_value = enriched_meal
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 1
        # Should save twice: once after mark_analyzing, once after mark_enriching
        assert self.meal_repository.save.call_count == 2
        self.meal_repository.save.assert_any_call(analyzing_meal)
        self.meal_repository.save.assert_any_call(enriched_meal)
        self.image_store.load.assert_called_once_with(self.test_image.image_id)
        self.vision_service.analyze.assert_called_once_with(b"fake image bytes")
        self.gpt_parser.parse_to_nutrition.assert_called_once_with(gpt_response)
        analyzing_meal.mark_ready.assert_called_once_with(nutrition)
        ready_meal.mark_enriching.assert_called_once_with("raw json")
    
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
        self.test_meal.mark_failed.return_value = failed_meal
        
        # Act
        result = self.job.run()
        
        # Assert
        assert result == 0  # No meals processed successfully
        # Should save twice: once after mark_analyzing, once after mark_failed
        assert self.meal_repository.save.call_count == 2
        self.meal_repository.save.assert_any_call(analyzing_meal)
        self.meal_repository.save.assert_any_call(failed_meal)
    
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
        assert result == 1  # Meal was processed (even though it failed)
        # Should save twice: once after mark_analyzing, once after mark_failed
        assert self.meal_repository.save.call_count == 2
        self.meal_repository.save.assert_any_call(analyzing_meal)
        self.meal_repository.save.assert_any_call(failed_meal)
        analyzing_meal.mark_failed.assert_called_once() 