"""
Integration test for manual meal creation with target date.
"""
import pytest
from datetime import datetime, date, timedelta
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand, ManualMealItem
from src.app.handlers.command_handlers.create_manual_meal_command_handler import CreateManualMealCommandHandler
from src.app.queries.activity import GetDailyActivitiesQuery
from src.app.handlers.query_handlers.activity_query_handlers import GetDailyActivitiesQueryHandler
from unittest.mock import Mock, MagicMock


@pytest.mark.asyncio
async def test_manual_meal_created_with_target_date():
    """Test that manual meals are created with the specified target date."""
    # Arrange
    mock_meal_repo = Mock()
    mock_food_service = Mock()
    mock_mapping_service = Mock()
    
    # Mock food data service response
    mock_food_service.get_multiple_foods = Mock(return_value=[
        {
            "fdcId": 168462,
            "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
        }
    ])
    
    # Mock mapping service response
    mock_mapping_service.map_food_details = Mock(return_value={
        "name": "Chicken Breast",
        "serving_size": 100.0,
        "calories": 165.0,
        "macros": {
            "protein": 31.0,
            "carbs": 0.0,
            "fat": 3.6,
        }
    })
    
    # Mock repository save - capture the saved meal
    saved_meal = None
    def save_meal(meal):
        nonlocal saved_meal
        saved_meal = meal
        return meal
    
    mock_meal_repo.save = save_meal
    
    # Create handler
    handler = CreateManualMealCommandHandler(
        meal_repository=mock_meal_repo,
        food_data_service=mock_food_service,
        mapping_service=mock_mapping_service
    )
    
    # Target date is yesterday
    target_date = date.today() - timedelta(days=1)
    
    # Create command with target date
    command = CreateManualMealCommand(
        user_id="test_user_123",
        items=[ManualMealItem(fdc_id=168462, quantity=150.0, unit="g")],
        dish_name="Grilled Chicken",
        meal_type="lunch",
        target_date=target_date
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert saved_meal is not None
    assert saved_meal.created_at.date() == target_date
    assert saved_meal.ready_at.date() == target_date
    assert saved_meal.meal_type == "lunch"
    assert saved_meal.dish_name == "Grilled Chicken"
    assert saved_meal.user_id == "test_user_123"
    
    # Verify nutrition was calculated correctly
    assert saved_meal.nutrition is not None
    assert saved_meal.nutrition.calories > 0
    assert saved_meal.nutrition.macros.protein > 0


@pytest.mark.asyncio
async def test_manual_meal_appears_in_daily_activities():
    """Test that manual meals appear in daily activities for the target date."""
    # Arrange
    target_date = date.today() - timedelta(days=1)
    target_datetime = datetime.combine(target_date, datetime.now().time())
    
    # Create a mock meal with target date
    mock_meal = MagicMock()
    mock_meal.meal_id = "meal_123"
    mock_meal.user_id = "test_user_123"
    mock_meal.created_at = target_datetime
    mock_meal.dish_name = "Grilled Chicken"
    mock_meal.meal_type = "lunch"
    mock_meal.status = MagicMock(value="READY")
    mock_meal.nutrition = MagicMock()
    mock_meal.nutrition.calories = 247.5
    mock_meal.nutrition.macros = MagicMock()
    mock_meal.nutrition.macros.protein = 46.5
    mock_meal.nutrition.macros.carbs = 0.0
    mock_meal.nutrition.macros.fat = 5.4
    mock_meal.nutrition.food_items = []
    mock_meal.image = MagicMock()
    mock_meal.image.url = None
    
    # Mock meal repository
    mock_meal_repo = Mock()
    mock_meal_repo.find_by_date = Mock(return_value=[mock_meal])
    
    # Create query handler
    handler = GetDailyActivitiesQueryHandler(meal_repository=mock_meal_repo)
    
    # Create query
    query = GetDailyActivitiesQuery(
        user_id="test_user_123",
        target_date=target_datetime
    )
    
    # Act
    activities = await handler.handle(query)
    
    # Assert
    assert len(activities) == 1
    activity = activities[0]
    assert activity["id"] == "meal_123"
    assert activity["type"] == "meal"
    assert activity["title"] == "Grilled Chicken"
    assert activity["meal_type"] == "lunch"
    assert activity["calories"] == 247.5
    assert activity["macros"]["protein"] == 46.5
    assert activity["macros"]["carbs"] == 0.0
    assert activity["macros"]["fat"] == 5.4


@pytest.mark.asyncio
async def test_manual_meal_without_target_date_uses_current_date():
    """Test that manual meals without target date use current date."""
    # Arrange
    mock_meal_repo = Mock()
    mock_food_service = Mock()
    mock_mapping_service = Mock()
    
    mock_food_service.get_multiple_foods = Mock(return_value=[
        {"fdcId": 168462, "description": "Chicken Breast"}
    ])
    
    mock_mapping_service.map_food_details = Mock(return_value={
        "name": "Chicken Breast",
        "serving_size": 100.0,
        "calories": 165.0,
        "macros": {"protein": 31.0, "carbs": 0.0, "fat": 3.6}
    })
    
    saved_meal = None
    def save_meal(meal):
        nonlocal saved_meal
        saved_meal = meal
        return meal
    
    mock_meal_repo.save = save_meal
    
    handler = CreateManualMealCommandHandler(
        meal_repository=mock_meal_repo,
        food_data_service=mock_food_service,
        mapping_service=mock_mapping_service
    )
    
    # Create command WITHOUT target date
    command = CreateManualMealCommand(
        user_id="test_user_123",
        items=[ManualMealItem(fdc_id=168462, quantity=150.0, unit="g")],
        dish_name="Grilled Chicken",
        meal_type="lunch",
        target_date=None  # No target date
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert saved_meal is not None
    assert saved_meal.created_at.date() == date.today()
    assert saved_meal.ready_at.date() == date.today()

