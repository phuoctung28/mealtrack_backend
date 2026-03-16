"""
Unit tests for meal command handlers.
"""
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch
import pytest

from src.app.commands.meal import (
    UploadMealImageImmediatelyCommand
)
from src.domain.model import MealStatus
from src.infra.database.uow import UnitOfWork


@pytest.mark.unit 
class TestUploadMealImageImmediatelyHandler:
    """Test UploadMealImageImmediatelyCommand handler."""
    
    @pytest.mark.asyncio
    async def test_upload_and_analyze_immediately_success(self, event_bus, sample_image_bytes, test_session):
        """Test successful immediate upload and analysis."""
        # Arrange
        command = UploadMealImageImmediatelyCommand(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act - patch UnitOfWork to use test_session (SQLite) instead of MySQL
        import src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler as handler_module
        original_uow = handler_module.UnitOfWork
        
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)
        
        handler_module.UnitOfWork = make_uow
        try:
            meal = await event_bus.send(command)
        finally:
            handler_module.UnitOfWork = original_uow
        
        # Assert
        assert meal.meal_id is not None
        assert meal.status == MealStatus.READY
        assert meal.dish_name == "Grilled Chicken with Rice"
        assert meal.nutrition is not None
        # calories derived from macros: 48*4 + 70*4 + 17*9 = 625.0
        assert meal.nutrition.calories == pytest.approx(625.0)
        assert len(meal.nutrition.food_items) == 3
    
    @pytest.mark.asyncio
    async def test_upload_and_analyze_immediately_stores_in_repository(
        self, event_bus, meal_repository, sample_image_bytes, test_session
    ):
        """Test that immediately analyzed meal is stored correctly."""
        # Arrange
        command = UploadMealImageImmediatelyCommand(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act - patch UnitOfWork to use test_session so handler and repository share same session
        import src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler as handler_module
        original_uow = handler_module.UnitOfWork
        
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)
        
        handler_module.UnitOfWork = make_uow
        try:
            meal = await event_bus.send(command)
        finally:
            handler_module.UnitOfWork = original_uow
        
        # Assert
        stored_meal = meal_repository.find_by_id(meal.meal_id)
        assert stored_meal is not None
        assert stored_meal.status == MealStatus.READY
        assert stored_meal.nutrition is not None

    @pytest.mark.asyncio
    async def test_upload_and_analyze_uses_preuploaded_meal_when_ids_provided(
        self,
        event_bus,
        sample_image_bytes,
        test_session,
        mock_image_store,
    ):
        """Worker-style path should update existing queued meal to READY."""
        from src.infra.database.models.enums import MealStatusEnum
        from src.infra.database.models.meal.meal import Meal as DBMeal
        from src.infra.database.models.meal.meal_image import MealImage as DBMealImage

        user_id = "550e8400-e29b-41d4-a716-446655440001"
        meal_id = str(uuid4())
        image_id = mock_image_store.save(sample_image_bytes, "image/jpeg")

        db_image = DBMealImage(
            image_id=image_id,
            format="jpeg",
            size_bytes=len(sample_image_bytes),
            url=f"mock://images/{image_id}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_session.add(db_image)
        test_session.flush()

        queued_meal = DBMeal(
            meal_id=meal_id,
            user_id=user_id,
            image_id=image_id,
            status=MealStatusEnum.PROCESSING,
            dish_name=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_session.add(queued_meal)
        test_session.commit()

        command = UploadMealImageImmediatelyCommand(
            user_id=user_id,
            meal_id=meal_id,
            image_id=image_id,
            image_url=f"mock://images/{image_id}",
            content_type="image/jpeg",
        )

        import src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler as handler_module
        original_uow = handler_module.UnitOfWork

        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)

        handler_module.UnitOfWork = make_uow
        try:
            meal = await event_bus.send(command)
        finally:
            handler_module.UnitOfWork = original_uow

        assert meal.meal_id == meal_id
        assert meal.status == MealStatus.READY
        assert meal.nutrition is not None