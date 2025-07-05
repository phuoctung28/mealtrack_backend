"""
Global pytest configuration and fixtures.
"""
import os
import pytest
from typing import Generator, Any
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.infra.database.config import Base
from src.infra.database.models.meal import Meal as MealModel
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.event_bus import PyMediatorEventBus, EventBus
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition, FoodItem
from src.domain.model.macros import Macros
from src.infra.repositories.meal_repository import MealRepository
from src.infra.adapters.mock_image_store import MockImageStore
from src.infra.adapters.mock_vision_ai_service import MockVisionAIService
from src.domain.parsers.gpt_response_parser import GPTResponseParser


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with rollback after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


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
    from src.app.handlers.command_handlers.meal_command_handlers import (
        UploadMealImageCommandHandler,
        RecalculateMealNutritionCommandHandler,
        AnalyzeMealImageCommandHandler
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
    from src.infra.repositories.user_repository import UserRepository
    from src.domain.services.tdee_service import TdeeService
    from src.infra.adapters.mock_meal_suggestion_service import MockMealSuggestionService
    
    event_bus = PyMediatorEventBus()
    
    # Create repositories
    user_repository = UserRepository(test_session)
    
    # Register command handlers
    event_bus.register_handler(
        "UploadMealImageCommand",
        UploadMealImageCommandHandler(
            image_store=mock_image_store,
            meal_repository=meal_repository,
            vision_service=mock_vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    event_bus.register_handler(
        "RecalculateMealNutritionCommand",
        RecalculateMealNutritionCommandHandler(meal_repository)
    )
    
    event_bus.register_handler(
        "AnalyzeMealImageCommand",
        AnalyzeMealImageCommandHandler(
            meal_repository=meal_repository,
            vision_service=mock_vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    event_bus.register_handler(
        "UploadMealImageImmediatelyCommand",
        UploadMealImageImmediatelyHandler(
            image_store=mock_image_store,
            meal_repository=meal_repository,
            vision_service=mock_vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    # Register query handlers
    event_bus.register_handler(
        "GetMealByIdQuery",
        GetMealByIdQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        "GetMealsByDateQuery",
        GetMealsByDateQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        "GetDailyMacrosQuery",
        GetDailyMacrosQueryHandler(meal_repository)
    )
    
    # Register user handlers
    event_bus.register_handler(
        "SaveUserOnboardingCommand",
        SaveUserOnboardingCommandHandler(
            user_repository=user_repository,
            tdee_service=TdeeService()
        )
    )
    
    event_bus.register_handler(
        "GetUserProfileQuery",
        GetUserProfileQueryHandler(user_repository)
    )
    
    # Register daily meal handlers
    event_bus.register_handler(
        "GenerateDailyMealSuggestionsCommand",
        GenerateDailyMealSuggestionsCommandHandler(
            user_repository=user_repository,
            meal_suggestion_service=MockMealSuggestionService()
        )
    )
    
    return event_bus


# Test Data Fixtures
@pytest.fixture
def sample_user(test_session) -> User:
    """Create a sample user for testing."""
    user = User(
        user_id="test-user-123",
        email="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def sample_user_profile(test_session, sample_user) -> UserProfile:
    """Create a sample user profile for testing."""
    profile = UserProfile(
        user_id=sample_user.user_id,
        age=30,
        gender="male",
        height_cm=175,
        weight_kg=70,
        activity_level="moderately_active",
        goal="maintain_weight",
        dietary_preferences=["vegetarian"],
        health_conditions=[],
        created_at=datetime.now()
    )
    test_session.add(profile)
    test_session.commit()
    return profile


@pytest.fixture
def sample_meal_domain() -> Meal:
    """Create a sample meal domain object."""
    return Meal(
        meal_id="test-meal-123",
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id="test-image-123",
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
                fiber=5.0
            ),
            food_items=[
                FoodItem(
                    name="Rice",
                    quantity=150.0,
                    unit="g",
                    calories=200.0,
                    macros=Macros(
                        protein=5.0,
                        carbs=40.0,
                        fat=2.0,
                        fiber=2.0
                    )
                ),
                FoodItem(
                    name="Chicken",
                    quantity=100.0,
                    unit="g",
                    calories=300.0,
                    macros=Macros(
                        protein=25.0,
                        carbs=10.0,
                        fat=18.0,
                        fiber=3.0
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
    meal_model = MealModel(
        meal_id=sample_meal_domain.meal_id,
        status=sample_meal_domain.status.value,
        dish_name=sample_meal_domain.dish_name,
        created_at=sample_meal_domain.created_at,
        ready_at=sample_meal_domain.ready_at,
        image_url=sample_meal_domain.image.url,
        image_id=sample_meal_domain.image.image_id,
        total_calories=sample_meal_domain.nutrition.calories,
        total_protein=sample_meal_domain.nutrition.macros.protein,
        total_carbs=sample_meal_domain.nutrition.macros.carbs,
        total_fat=sample_meal_domain.nutrition.macros.fat,
        total_fiber=sample_meal_domain.nutrition.macros.fiber
    )
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


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")