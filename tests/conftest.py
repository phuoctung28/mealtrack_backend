"""
Global pytest configuration and fixtures.
"""
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.domain.model.macros import Macros
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition, FoodItem
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.infra.adapters.mock_image_store import MockImageStore
from src.infra.adapters.mock_vision_ai_service import MockVisionAIService
from src.infra.database.config import Base
# Import all models to ensure they're registered with Base metadata
from src.infra.database.models.meal.meal import Meal as MealModel
from src.infra.database.models.meal.meal_image import MealImage as MealImageModel
from src.infra.database.models.nutrition.food_item import FoodItem as FoodItemModel
from src.infra.database.models.nutrition.nutrition import Nutrition as NutritionModel
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.database.test_config import (
    get_test_database_url,
    create_test_engine
)
from src.infra.event_bus import PyMediatorEventBus, EventBus
from src.infra.repositories.meal_repository import MealRepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine(worker_id):
    """Create a test database engine."""
    engine = create_test_engine()
    
    # Create test database if it doesn't exist
    temp_engine = create_engine(
        get_test_database_url().rsplit('/', 1)[0],
        isolation_level='AUTOCOMMIT'
    )
    try:
        with temp_engine.connect() as conn:
            db_name = get_test_database_url().rsplit('/', 1)[1].split('?')[0]
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
    finally:
        temp_engine.dispose()
    
    # Import models to ensure they're registered

    # Only one worker should create tables to avoid race conditions
    if worker_id in ("master", "gw0"):
        # Drop all tables first to ensure clean state
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            Base.metadata.drop_all(bind=engine)
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
    # Other workers wait a bit for tables to be created
    elif worker_id != "master":
        import time
        time.sleep(2)
    
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with rollback after each test."""
    # Create a new connection for each test
    connection = test_engine.connect()
    
    # Start a transaction
    transaction = connection.begin()
    
    # Create a session bound to this connection
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    # Configure the session to use this specific connection
    session.connection = connection
    
    try:
        yield session
    finally:
        # Always clean up, even if test fails
        session.close()
        try:
            transaction.rollback()
        except Exception:
            pass  # Transaction might already be closed
        try:
            connection.close()
        except Exception:
            pass  # Connection might already be closed


@pytest.fixture
def mock_image_store() -> MockImageStore:
    """Mock image store for testing."""
    return MockImageStore()


@pytest.fixture
def mock_vision_service() -> MockVisionAIService:
    """Mock vision AI service for testing."""
    return MockVisionAIService()


@pytest.fixture
def gpt_parser() -> GPTResponseParser:
    """GPT response parser for testing."""
    return GPTResponseParser()


@pytest.fixture
def meal_repository(test_session) -> MealRepository:
    """Meal repository with test database session."""
    return MealRepository(test_session)


@pytest.fixture
def event_bus(
    test_session,
    mock_image_store,
    mock_vision_service,
    gpt_parser,
    meal_repository
) -> EventBus:
    """Configured event bus for testing."""
    # Import handlers
    from src.app.handlers.command_handlers.meal_command_handlers import (
        UploadMealImageCommandHandler,
        RecalculateMealNutritionCommandHandler,
        EditMealCommandHandler,
        AddCustomIngredientCommandHandler
    )
    from src.app.handlers.command_handlers.upload_meal_image_immediately_handler import (
        UploadMealImageImmediatelyHandler
    )
    from src.app.handlers.query_handlers.meal_query_handlers import (
        GetMealByIdQueryHandler,
        GetMealsByDateQueryHandler,
        GetDailyMacrosQueryHandler
    )
    from src.app.handlers.command_handlers.user_command_handlers import (
        SaveUserOnboardingCommandHandler
    )
    from src.app.handlers.command_handlers.daily_meal_command_handlers import (
        GenerateDailyMealSuggestionsCommandHandler
    )
    from src.app.handlers.query_handlers.user_query_handlers import (
        GetUserProfileQueryHandler
    )
    
    # Import commands and queries
    from src.app.commands.meal.upload_meal_image_command import UploadMealImageCommand
    from src.app.commands.meal.recalculate_meal_nutrition_command import RecalculateMealNutritionCommand
    from src.app.commands.meal.upload_meal_image_immediately_command import UploadMealImageImmediatelyCommand
    from src.app.commands.meal.edit_meal_command import EditMealCommand, AddCustomIngredientCommand
    from src.app.queries.meal.get_meal_by_id_query import GetMealByIdQuery
    from src.app.queries.meal.get_meals_by_date_query import GetMealsByDateQuery
    from src.app.queries.meal.get_daily_macros_query import GetDailyMacrosQuery
    from src.app.commands.user.save_user_onboarding_command import SaveUserOnboardingCommand
    from src.app.queries.user.get_user_profile_query import GetUserProfileQuery
    from src.app.commands.daily_meal.generate_daily_meal_suggestions_command import GenerateDailyMealSuggestionsCommand
    from src.infra.repositories.user_repository import UserRepository
    from src.domain.services.tdee_service import TdeeCalculationService
    from src.infra.adapters.mock_meal_suggestion_service import MockMealSuggestionService
    
    event_bus = PyMediatorEventBus()
    
    # Create repositories
    user_repository = UserRepository(test_session)
    
    # Register command handlers
    event_bus.register_handler(
        UploadMealImageCommand,
        UploadMealImageCommandHandler(
            image_store=mock_image_store,
            meal_repository=meal_repository
        )
    )
    
    event_bus.register_handler(
        RecalculateMealNutritionCommand,
        RecalculateMealNutritionCommandHandler(meal_repository)
    )
    
    # Register meal edit command handlers
    event_bus.register_handler(
        EditMealCommand,
        EditMealCommandHandler(
            meal_repository=meal_repository,
            food_service=None,  # Mock if needed
            nutrition_calculator=None
        )
    )
    
    event_bus.register_handler(
        AddCustomIngredientCommand,
        AddCustomIngredientCommandHandler(
            meal_repository=meal_repository
        )
    )

    # Delete (soft delete) handler
    from src.app.commands.meal.delete_meal_command import DeleteMealCommand
    from src.app.handlers.command_handlers.meal_command_handlers import DeleteMealCommandHandler
    event_bus.register_handler(
        DeleteMealCommand,
        DeleteMealCommandHandler(meal_repository)
    )
    
    event_bus.register_handler(
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            image_store=mock_image_store,
            meal_repository=meal_repository,
            vision_service=mock_vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    # Register query handlers
    event_bus.register_handler(
        GetMealByIdQuery,
        GetMealByIdQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        GetMealsByDateQuery,
        GetMealsByDateQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        GetDailyMacrosQuery,
        GetDailyMacrosQueryHandler(meal_repository)
    )
    
    # Register user handlers
    save_user_handler = SaveUserOnboardingCommandHandler(db=test_session)
    event_bus.register_handler(
        SaveUserOnboardingCommand,
        save_user_handler
    )
    
    event_bus.register_handler(
        GetUserProfileQuery,
        GetUserProfileQueryHandler(test_session)
    )
    
    # Register daily meal handlers
    mock_suggestion_service = MockMealSuggestionService()
    event_bus.register_handler(
        GenerateDailyMealSuggestionsCommand,
        GenerateDailyMealSuggestionsCommandHandler(
            suggestion_service=mock_suggestion_service,
            tdee_service=TdeeCalculationService()
        )
    )
    
    return event_bus


# Test Data Fixtures
@pytest.fixture
def sample_user(test_session) -> User:
    """Create a sample user for testing."""
    user = User(
        id="550e8400-e29b-41d4-a716-446655440001",
        firebase_uid="test-firebase-uid-123",
        email="test@example.com",
        username="testuser",
        password_hash="dummy_hash_for_test",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def sample_user_profile(test_session, sample_user) -> UserProfile:
    """Create a sample user profile for testing."""
    profile = UserProfile(
        user_id=sample_user.id,
        age=30,
        gender="male",
        height_cm=175,
        weight_kg=70,
        activity_level="moderate",
        fitness_goal="maintenance",
        dietary_preferences=["vegetarian"],
        health_conditions=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    test_session.add(profile)
    test_session.commit()
    return profile


@pytest.fixture
def sample_meal_domain() -> Meal:
    """Create a sample meal domain object."""
    return Meal(
        meal_id="123e4567-e89b-12d3-a456-426614174001",
        user_id="123e4567-e89b-12d3-a456-426614174000",
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id="123e4567-e89b-12d3-a456-426614174002",
            format="jpeg",
            size_bytes=100000,
            url="https://example.com/image.jpg"
        ),
        dish_name="Test Meal",
        nutrition=Nutrition(
            calories=500.0,
            macros=Macros(
                protein=30.0,
                carbs=50.0,
                fat=20.0,
            ),
            food_items=[
                FoodItem(
                    id="sample-rice-id",
                    name="Rice",
                    quantity=150.0,
                    unit="g",
                    calories=200.0,
                    macros=Macros(
                        protein=5.0,
                        carbs=40.0,
                        fat=2.0,
                    )
                ),
                FoodItem(
                    id="sample-chicken-id",
                    name="Chicken",
                    quantity=100.0,
                    unit="g",
                    calories=300.0,
                    macros=Macros(
                        protein=25.0,
                        carbs=10.0,
                        fat=18.0,
                    )
                )
            ],
            confidence_score=0.95
        ),
        ready_at=datetime.now()
    )


@pytest.fixture
def sample_meal_db(test_session, sample_meal_domain) -> MealModel:
    """Create a sample meal in the database."""
    # First create the meal image
    meal_image = MealImageModel.from_domain(sample_meal_domain.image)
    test_session.add(meal_image)
    test_session.flush()
    
    # Create meal using from_domain method
    meal_model = MealModel.from_domain(sample_meal_domain)
    test_session.add(meal_model)
    test_session.commit()
    return meal_model


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Sample image bytes for testing."""
    # Simple 1x1 red pixel JPEG
    return bytes.fromhex(
        'ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232ffc00011080001000103012200021101031101ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090a0bffc400b51100020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00e2ffd9'
    )


@pytest.fixture
def sample_meal_with_nutrition(test_session) -> Meal:
    """Create a sample meal with nutrition for editing tests."""
    import uuid
    
    # Create food items with IDs for editing
    food_items = [
        FoodItem(
            name="Grilled Chicken",
            quantity=150.0,
            unit="g",
            calories=248.0,
            macros=Macros(
                protein=46.2,
                carbs=0.0,
                fat=5.4,
            ),
            id=str(uuid.uuid4()),
            fdc_id=171077,
            is_custom=False
        ),
        FoodItem(
            name="Brown Rice",
            quantity=100.0,
            unit="g",
            calories=112.0,
            macros=Macros(
                protein=2.6,
                carbs=22.0,
                fat=0.9,
            ),
            id=str(uuid.uuid4()),
            fdc_id=168880,
            is_custom=False
        ),
        FoodItem(
            name="Mixed Vegetables",
            quantity=80.0,
            unit="g",
            calories=35.0,
            macros=Macros(
                protein=1.5,
                carbs=7.0,
                fat=0.2,
            ),
            id=str(uuid.uuid4()),
            is_custom=True
        )
    ]
    
    meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id="550e8400-e29b-41d4-a716-446655440001",
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=100000,
            url="https://example.com/meal.jpg"
        ),
        dish_name="Grilled Chicken with Rice and Vegetables",
        nutrition=Nutrition(
            calories=395.0,
            macros=Macros(
                protein=50.3,
                carbs=29.0,
                fat=6.5,
            ),
            food_items=food_items,
            confidence_score=0.9
        ),
        ready_at=datetime.now(),
        edit_count=0,
        is_manually_edited=False
    )
    
    # Store in database
    meal_image_model = MealImageModel.from_domain(meal.image)
    test_session.add(meal_image_model)
    test_session.flush()
    
    meal_model = MealModel.from_domain(meal)
    test_session.add(meal_model)
    test_session.commit()
    
    return meal


@pytest.fixture
def sample_meal_processing(test_session) -> Meal:
    """Create a sample meal in PROCESSING status for testing."""
    import uuid
    
    meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id="550e8400-e29b-41d4-a716-446655440001",
        status=MealStatus.PROCESSING,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=100000,
            url="https://example.com/processing.jpg"
        )
    )
    
    # Store in database
    meal_image_model = MealImageModel.from_domain(meal.image)
    test_session.add(meal_image_model)
    test_session.flush()
    
    meal_model = MealModel.from_domain(meal)
    test_session.add(meal_model)
    test_session.commit()
    
    return meal


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")