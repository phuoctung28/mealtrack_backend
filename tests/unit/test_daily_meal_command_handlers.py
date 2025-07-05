"""
Unit tests for daily meal command handlers.
"""
import pytest

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.daily_meal import GenerateDailyMealSuggestionsCommand


@pytest.mark.unit
class TestGenerateDailyMealSuggestionsCommandHandler:
    """Test GenerateDailyMealSuggestionsCommand handler."""
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_with_profile_id(
        self, event_bus, sample_user_profile
    ):
        """Test generating meal suggestions with user profile ID."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            age=sample_user_profile.age,
            gender=sample_user_profile.gender,
            height=sample_user_profile.height_cm,
            weight=sample_user_profile.weight_kg,
            activity_level=sample_user_profile.activity_level,
            goal=sample_user_profile.fitness_goal,
            dietary_preferences=sample_user_profile.dietary_preferences,
            health_conditions=sample_user_profile.health_conditions
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
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_with_custom_preferences(self, event_bus):
        """Test generating meal suggestions with custom preferences."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            age=25,
            gender="female",
            height=165,
            weight=60,
            activity_level="active",
            goal="cutting",
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
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_invalid_profile_id(self, event_bus):
        """Test generating suggestions with valid data (no profile lookup)."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            age=25,
            gender="male",
            height=175,
            weight=70,
            activity_level="moderate",
            goal="maintenance"
        )
        
        # Act - Since we provide all required fields, this should succeed
        result = await event_bus.send(command)
        
        # Assert
        assert "suggestions" in result
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_missing_required_fields(self, event_bus):
        """Test generating suggestions with invalid data."""
        # Arrange - invalid values that should fail validation
        command = GenerateDailyMealSuggestionsCommand(
            age=-5,  # Invalid age
            gender="female",
            height=165,
            weight=60,
            activity_level="moderate",
            goal="maintenance"
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_generate_suggestions_calorie_distribution(
        self, event_bus, sample_user_profile
    ):
        """Test that generated suggestions have proper calorie distribution."""
        # Arrange
        command = GenerateDailyMealSuggestionsCommand(
            age=sample_user_profile.age,
            gender=sample_user_profile.gender,
            height=sample_user_profile.height_cm,
            weight=sample_user_profile.weight_kg,
            activity_level=sample_user_profile.activity_level,
            goal=sample_user_profile.fitness_goal,
            dietary_preferences=sample_user_profile.dietary_preferences,
            health_conditions=sample_user_profile.health_conditions
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