"""
Test user-specific daily activities functionality.
"""
from datetime import datetime, date
from unittest.mock import Mock

import pytest

from src.app.handlers.query_handlers import GetDailyActivitiesQueryHandler
from src.app.queries.activity.get_daily_activities_query import GetDailyActivitiesQuery
from src.domain.model import Macros, Meal, MealStatus, MealImage, Nutrition


@pytest.mark.asyncio
class TestUserSpecificActivities:
    """Test user-specific daily activities functionality."""
    
    async def test_activities_filtered_by_user(self):
        """Test that activities are properly filtered by user_id."""
        # Create mock meals for different users
        user1_meal = Meal(
            meal_id="123e4567-e89b-12d3-a456-426614174001",
            user_id="123e4567-e89b-12d3-a456-426614174100",
            status=MealStatus.READY,
            created_at=datetime(2024, 8, 15, 12, 0, 0),
            image=MealImage(
                image_id="123e4567-e89b-12d3-a456-426614174010",
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/img1.jpg"
            ),
            dish_name="User 1 Lunch",
            nutrition=Nutrition(
                calories=500.0,
                macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime(2024, 8, 15, 12, 5, 0)
        )
        
        user2_meal = Meal(
            meal_id="123e4567-e89b-12d3-a456-426614174002",
            user_id="123e4567-e89b-12d3-a456-426614174200",
            status=MealStatus.READY,
            created_at=datetime(2024, 8, 15, 13, 0, 0),
            image=MealImage(
                image_id="123e4567-e89b-12d3-a456-426614174020",
                format="jpeg",
                size_bytes=200000,
                url="https://example.com/img2.jpg"
            ),
            dish_name="User 2 Lunch",
            nutrition=Nutrition(
                calories=600.0,
                macros=Macros(protein=35.0, carbs=60.0, fat=25.0),
                food_items=[],
                confidence_score=0.95
            ),
            ready_at=datetime(2024, 8, 15, 13, 5, 0)
        )
        
        # Create mock repository
        mock_repo = Mock()
        
        # Configure repository to return different meals for different users
        def mock_find_by_date(target_date, user_id=None, limit=50):
            all_meals = [user1_meal, user2_meal]
            if user_id == "123e4567-e89b-12d3-a456-426614174100":
                return [user1_meal]
            elif user_id == "123e4567-e89b-12d3-a456-426614174200":
                return [user2_meal]
            else:
                return all_meals
        
        mock_repo.find_by_date.side_effect = mock_find_by_date
        
        # Create handler
        handler = GetDailyActivitiesQueryHandler()
        handler.set_dependencies(mock_repo)
        
        # Test for user 1
        query_user1 = GetDailyActivitiesQuery(
            user_id="123e4567-e89b-12d3-a456-426614174100",
            target_date=datetime(2024, 8, 15)
        )
        
        activities_user1 = await handler.handle(query_user1)
        
        # Verify user 1 only gets their meal
        assert len(activities_user1) == 1
        assert activities_user1[0]["id"] == "123e4567-e89b-12d3-a456-426614174001"
        assert activities_user1[0]["title"] == "User 1 Lunch"
        
        # Test for user 2
        query_user2 = GetDailyActivitiesQuery(
            user_id="123e4567-e89b-12d3-a456-426614174200",
            target_date=datetime(2024, 8, 15)
        )
        
        activities_user2 = await handler.handle(query_user2)
        
        # Verify user 2 only gets their meal
        assert len(activities_user2) == 1
        assert activities_user2[0]["id"] == "123e4567-e89b-12d3-a456-426614174002"
        assert activities_user2[0]["title"] == "User 2 Lunch"
        
        # Verify repository was called with correct parameters
        actual_calls = mock_repo.find_by_date.call_args_list
        assert len(actual_calls) == 2
        
        # Check that user_id was passed correctly
        assert actual_calls[0][1]["user_id"] == "123e4567-e89b-12d3-a456-426614174100"
        assert actual_calls[1][1]["user_id"] == "123e4567-e89b-12d3-a456-426614174200"
    
    async def test_empty_activities_for_user_with_no_meals(self):
        """Test that users with no meals get empty activities list."""
        # Create mock repository that returns no meals
        mock_repo = Mock()
        mock_repo.find_by_date.return_value = []
        
        # Create handler
        handler = GetDailyActivitiesQueryHandler()
        handler.set_dependencies(mock_repo)
        
        # Test query
        query = GetDailyActivitiesQuery(
            user_id="123e4567-e89b-12d3-a456-426614174300",
            target_date=datetime(2024, 8, 15)
        )
        
        activities = await handler.handle(query)
        
        # Verify empty result
        assert activities == []
        
        # Verify repository was called with correct user_id
        mock_repo.find_by_date.assert_called_once_with(
            date(2024, 8, 15),
            user_id="123e4567-e89b-12d3-a456-426614174300"
        )