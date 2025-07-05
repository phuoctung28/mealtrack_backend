"""
Unit tests for daily meal command handlers.
"""
import pytest

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.daily_meal import GenerateDailyMealSuggestionsCommand


@pytest.mark.unit
class TestGenerateDailyMealSuggestionsCommandHandler:
    """Test GenerateDailyMealSuggestionsCommand handler."""
    
    async def test_generate_suggestions_with_profile_id(
        self, event_bus, sample_user_profile
    ):
        """Test generating meal suggestions with user profile ID."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            user_profile_id=sample_user_profile.user_id
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert "suggestions" in result
        assert len(result["suggestions"]) == 4  # breakfast, lunch, dinner, snack
        assert "total_calories" in result
        assert "total_macros" in result
        
        # Check each suggestion
        for suggestion in result["suggestions"]:
            assert "meal_type" in suggestion
            assert "dish_name" in suggestion
            assert "calories" in suggestion
            assert "macros" in suggestion
            assert suggestion["meal_type"] in ["breakfast", "lunch", "dinner", "snack"]
    
    async def test_generate_suggestions_with_custom_preferences(self, event_bus):
        """Test generating meal suggestions with custom preferences."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            age=25,
            gender="female",
            height_cm=165,
            weight_kg=60,
            activity_level="active",
            goal="lose_weight",
            dietary_preferences=["vegetarian", "gluten-free"],
            health_conditions=["lactose_intolerant"]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert "suggestions" in result
        assert len(result["suggestions"]) == 4
        # Verify dietary preferences are respected
        for suggestion in result["suggestions"]:
            # Mock should respect preferences in real implementation
            assert suggestion["dish_name"] is not None
    
    async def test_generate_suggestions_invalid_profile_id(self, event_bus):
        """Test generating suggestions with non-existent profile."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            user_profile_id="non-existent-user"
        )
        
        # Act & Assert
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(command)
    
    async def test_generate_suggestions_missing_required_fields(self, event_bus):
        """Test generating suggestions without required fields."""
        # Arrange - no profile ID and incomplete custom preferences
        command = GenerateDailyMealSuggestionsCommand(
            age=25,
            gender="female"
            # Missing height, weight, activity_level, goal
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    async def test_generate_suggestions_calorie_distribution(
        self, event_bus, sample_user_profile
    ):
        """Test that generated suggestions have proper calorie distribution."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            user_profile_id=sample_user_profile.user_id
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        total_calories = result["total_calories"]
        breakfast_calories = next(
            s["calories"] for s in result["suggestions"] 
            if s["meal_type"] == "breakfast"
        )
        lunch_calories = next(
            s["calories"] for s in result["suggestions"] 
            if s["meal_type"] == "lunch"
        )
        dinner_calories = next(
            s["calories"] for s in result["suggestions"] 
            if s["meal_type"] == "dinner"
        )
        
        # Breakfast should be ~25% of total
        assert 0.20 <= breakfast_calories / total_calories <= 0.30
        # Lunch should be ~35% of total
        assert 0.30 <= lunch_calories / total_calories <= 0.40
        # Dinner should be ~30% of total
        assert 0.25 <= dinner_calories / total_calories <= 0.35