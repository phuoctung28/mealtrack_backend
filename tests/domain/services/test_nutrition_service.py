import pytest
from unittest.mock import Mock
from typing import Dict, Optional

from domain.model.nutrition import Nutrition, FoodItem
from domain.model.macros import Macros
from domain.ports.food_database_port import FoodDatabasePort
from domain.services.nutrition_service import NutritionService, EnrichmentResult

class TestNutritionService:
    """Tests for the NutritionService domain service."""
    
    def test_merge_with_database_lookups(self):
        """Test merging AI nutrition with database lookup results."""
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        # Create AI nutrition data
        ai_food_items = [
            FoodItem(
                name="chicken breast",
                quantity=150,
                unit="g",
                calories=200,
                macros=Macros(protein=35, carbs=0, fat=5),
                confidence=0.6
            ),
            FoodItem(
                name="unknown food",
                quantity=100,
                unit="g", 
                calories=100,
                macros=Macros(protein=5, carbs=10, fat=2),
                confidence=0.7
            )
        ]
        
        ai_nutrition = Nutrition(
            calories=300,
            macros=Macros(protein=40, carbs=10, fat=7),
            food_items=ai_food_items,
            confidence_score=0.65
        )
        
        # Create database lookup results (only first item found)
        db_lookup_result = FoodItem(
            name="chicken breast",
            quantity=150,
            unit="g",
            calories=248,  # More accurate database value
            macros=Macros(protein=46.5, carbs=0, fat=5.4),  # More accurate
            confidence=0.9  # High confidence for DB data
        )
        
        database_lookups = {
            "chicken breast": db_lookup_result,
            "unknown food": None  # Not found in database
        }
        
        # Act
        result = service.merge(ai_nutrition, database_lookups)
        
        # Assert
        assert len(result.food_items) == 2
        
        # First item should use database data
        assert result.food_items[0].name == "chicken breast"
        assert result.food_items[0].calories == 248
        assert result.food_items[0].macros.protein == 46.5
        assert result.food_items[0].confidence == 0.9
        
        # Second item should use AI data with reduced confidence
        assert result.food_items[1].name == "unknown food"
        assert result.food_items[1].calories == 100
        assert result.food_items[1].confidence <= 0.4  # Reduced confidence
        
        # Totals should be recalculated
        assert result.calories == 348  # 248 + 100
        assert result.macros.protein == 51.5  # 46.5 + 5
        assert result.macros.carbs == 10  # 0 + 10
        assert result.macros.fat == 7.4  # 5.4 + 2
        
        # Overall confidence should be weighted average
        assert 0.7 <= result.confidence_score <= 0.8
    
    def test_enrich_nutrition_with_batch_lookup(self):
        """Test the complete enrichment process."""
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        # Create AI nutrition
        ai_food_items = [
            FoodItem(
                name="salmon",
                quantity=120,
                unit="g",
                calories=180,
                macros=Macros(protein=20, carbs=0, fat=10),
                confidence=0.5
            )
        ]
        
        ai_nutrition = Nutrition(
            calories=180,
            macros=Macros(protein=20, carbs=0, fat=10),
            food_items=ai_food_items,
            confidence_score=0.5
        )
        
        # Mock batch lookup response
        db_result = FoodItem(
            name="salmon",
            quantity=120,
            unit="g",
            calories=249,
            macros=Macros(protein=26.4, carbs=0, fat=14.4),
            confidence=0.9
        )
        
        mock_food_db.lookup_batch.return_value = {"salmon": db_result}
        
        # Act
        enrichment_result = service.enrich_nutrition(ai_nutrition)
        
        # Assert
        assert isinstance(enrichment_result, EnrichmentResult)
        assert enrichment_result.enriched_items == 1
        assert len(enrichment_result.failed_lookups) == 0
        
        # Check enhanced nutrition
        enhanced = enrichment_result.nutrition
        assert enhanced.calories == 249
        assert enhanced.macros.protein == 26.4
        assert enhanced.confidence_score > 0.5  # Should be higher due to DB lookup
        
        # Verify batch lookup was called correctly
        mock_food_db.lookup_batch.assert_called_once()
        call_args = mock_food_db.lookup_batch.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["name"] == "salmon"
        assert call_args[0]["quantity"] == 120
        assert call_args[0]["unit"] == "g"
    
    def test_calculate_total_calories_rounding(self):
        """Test that calories are rounded to ±1 kcal as per acceptance criteria."""
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        food_items = [
            FoodItem("food1", 100, "g", 123.4, Macros(10, 15, 8), confidence=0.8),
            FoodItem("food2", 100, "g", 156.7, Macros(12, 20, 6), confidence=0.9)
        ]
        
        # Act
        total_calories = service._calculate_total_calories(food_items)
        
        # Assert
        expected = round(123.4 + 156.7, 1)  # Should be 280.1
        assert total_calories == expected
        assert isinstance(total_calories, float)
    
    def test_validate_nutrition_totals_consistent(self):
        """Test validation of consistent nutrition totals."""
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        food_items = [
            FoodItem("food1", 100, "g", 100, Macros(10, 10, 5), confidence=0.8),
            FoodItem("food2", 100, "g", 200, Macros(20, 30, 10), confidence=0.9)
        ]
        
        # Create nutrition with correct totals
        nutrition = Nutrition(
            calories=300,  # 100 + 200
            macros=Macros(protein=30, carbs=40, fat=15),  # 10+20, 10+30, 5+10
            food_items=food_items,
            confidence_score=0.85
        )
        
        # Act
        is_valid = service.validate_nutrition_totals(nutrition)
        
        # Assert
        assert is_valid is True
    
    def test_validate_nutrition_totals_inconsistent(self):
        """Test validation fails for inconsistent nutrition totals.""" 
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        food_items = [
            FoodItem("food1", 100, "g", 100, Macros(10, 10, 5), confidence=0.8)
        ]
        
        # Create nutrition with incorrect totals (off by more than 1 kcal)
        nutrition = Nutrition(
            calories=150,  # Should be 100, off by 50
            macros=Macros(protein=10, carbs=10, fat=5),
            food_items=food_items,
            confidence_score=0.8
        )
        
        # Act
        is_valid = service.validate_nutrition_totals(nutrition)
        
        # Assert
        assert is_valid is False
    
    def test_enrich_nutrition_no_food_items(self):
        """Test enrichment with no food items returns original nutrition."""
        # Arrange
        mock_food_db = Mock(spec=FoodDatabasePort)
        service = NutritionService(mock_food_db)
        
        ai_nutrition = Nutrition(
            calories=300,
            macros=Macros(protein=20, carbs=40, fat=10),
            food_items=None,  # No food items
            confidence_score=0.6
        )
        
        # Act
        result = service.enrich_nutrition(ai_nutrition)
        
        # Assert
        assert result.nutrition == ai_nutrition
        assert result.enriched_items == 0
        assert len(result.failed_lookups) == 0
        
        # Should not call database
        mock_food_db.lookup_batch.assert_not_called() 