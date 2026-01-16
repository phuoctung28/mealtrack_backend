"""
Shared fixtures for API integration tests.

Provides FastAPI TestClient with SQLite database and mocked external services.
Only 3rd party services are mocked - application services use real implementations.
"""
from unittest.mock import Mock, AsyncMock, patch
from typing import Generator, Optional
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.base_dependencies import (
    get_db,
    get_cache_service,
    get_food_cache_service,
    get_food_data_service,
    get_ai_chat_service,
)
from src.api.dependencies.auth import get_current_user_id
from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from tests.fixtures.mock_adapters.mock_vision_ai_service import MockVisionAIService


@pytest.fixture
def api_client(test_session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with SQLite session and mocked 3rd party services.
    
    MOCKED (3rd party services):
    - Redis/Cache: Mocked to avoid Redis dependency
    - Cloudinary/ImageStore: Mocked to avoid external API calls
    - Vision AI: Mocked with realistic responses
    - Gemini/AI services: Mocked to avoid external API calls
    
    REAL (application services):
    - Event bus handlers
    - Domain services
    - Repositories (using SQLite test database)
    """
    from src.infra.database.uow import UnitOfWork
    from src.infra.config.settings import settings
    import src.api.base_dependencies as base_deps_module
    import src.api.dependencies.event_bus as event_bus_module
    
    # Reset singletons before setting up client
    event_bus_module._configured_event_bus = None
    base_deps_module._image_store = None
    base_deps_module._vision_service = None
    base_deps_module._gpt_parser = None
    base_deps_module._suggestion_service = None
    
    # Store originals for restoration
    original_uow_init = UnitOfWork.__init__
    original_cache_enabled = settings.CACHE_ENABLED
    original_redis = base_deps_module._redis_client
    original_cache = base_deps_module._cache_service
    
    # === Patch UnitOfWork to use test_session ===
    def patched_uow_init(self, session=None):
        if session is None:
            session = test_session
        original_uow_init(self, session)
    
    UnitOfWork.__init__ = patched_uow_init
    
    # === Mock Redis/Cache (3rd party) ===
    settings.CACHE_ENABLED = False
    # Mock Redis Client with actual storage for tests (so sessions persist)
    _mock_redis_storage = {}
    
    class MockRedisClient:
        """Mock Redis client that actually stores data in memory."""
        def __init__(self):
            self.storage = _mock_redis_storage
        
        async def connect(self):
            pass
        
        async def disconnect(self):
            pass
        
        async def get(self, key: str):
            return self.storage.get(key)
        
        async def set(self, key: str, value: str, ttl: int = None):
            self.storage[key] = value
            return True
        
        async def delete(self, key: str):
            self.storage.pop(key, None)
            return True
        
        async def ttl(self, key: str):
            # Return a default TTL for tests
            return 3600 if key in self.storage else -1
        
        @property
        def client(self):
            """Return self for TTL operations."""
            return self
    
    mock_redis = MockRedisClient()
    base_deps_module._redis_client = mock_redis
    
    # Mock Cache Service with actual storage (shares storage with Redis for consistency)
    class MockCacheService:
        """Mock cache service that actually stores data in memory."""
        def __init__(self):
            self.storage = _mock_redis_storage  # Share storage with Redis
        
        async def get(self, key: str):
            return self.storage.get(key)
        
        async def set(self, key: str, value: str, ttl: int = None):
            self.storage[key] = value
            return True
        
        async def get_json(self, key: str):
            import json
            value = self.storage.get(key)
            return json.loads(value) if value else None
        
        async def set_json(self, key: str, value: dict, ttl: int = None):
            import json
            self.storage[key] = json.dumps(value)
            return True
        
        async def invalidate(self, key: str):
            self.storage.pop(key, None)
            return True
        
        async def invalidate_pattern(self, pattern: str):
            # Simple pattern matching for tests
            import re
            regex = pattern.replace("*", ".*")
            keys_to_delete = [k for k in self.storage.keys() if re.match(regex, k)]
            for k in keys_to_delete:
                self.storage.pop(k, None)
            return True
    
    mock_cache = MockCacheService()
    base_deps_module._cache_service = mock_cache
    
    # === Mock Image Store (Cloudinary - 3rd party) ===
    from uuid import uuid4
    from src.domain.ports.image_store_port import ImageStorePort
    
    class MockImageStore(ImageStorePort):
        """Mock image store that implements ImageStorePort."""
        def save(self, image_bytes: bytes, content_type: str) -> str:
            """Return a UUID string as image_id (matches CloudinaryImageStore.save signature)."""
            return str(uuid4())
        
        def load(self, image_id: str) -> Optional[bytes]:
            """Mock load - return None (not used in tests)."""
            return None
        
        def get_url(self, image_id: str) -> Optional[str]:
            """Return mock URL for image."""
            return f"https://mock-cloudinary.com/{image_id}.jpg"
        
        def delete(self, image_id: str) -> bool:
            """Mock delete - always succeeds."""
            return True
    
    mock_image_store = MockImageStore()
    base_deps_module._image_store = mock_image_store
    
    # === Mock Vision AI Service (Google Gemini - 3rd party) ===
    mock_vision = MockVisionAIService()
    base_deps_module._vision_service = mock_vision
    
    # === Mock GPT Parser (Uses Gemini - 3rd party) ===
    from src.domain.parsers.gpt_response_parser import GPTResponseParser
    mock_gpt_parser = GPTResponseParser()  # Use real parser, it just processes data
    base_deps_module._gpt_parser = mock_gpt_parser
    
    # === Patch SessionLocal and ScopedSession to use test_session for real services ===
    # This allows real application services to use the test database
    import src.infra.database.config as db_config_module
    original_session_local = db_config_module.SessionLocal
    original_scoped_session = db_config_module.ScopedSession
    
    def test_session_local():
        """Return test session instead of creating new connection."""
        return test_session
    
    # Create a mock scoped_session that always returns test_session
    class TestScopedSession:
        """Mock scoped_session that returns test_session."""
        def __call__(self):
            return test_session
        
        def remove(self):
            """No-op for cleanup."""
            pass
    
    # Patch SessionLocal and ScopedSession in the config module
    db_config_module.SessionLocal = test_session_local
    db_config_module.ScopedSession = TestScopedSession()
    
    # === Mock AI Chat Service (3rd party - Gemini) ===
    # The real services will use this mocked AI instead of calling Gemini
    mock_ai_chat = Mock()
    mock_ai_chat.invoke = AsyncMock(return_value="Mocked AI response")
    mock_ai_chat.stream = AsyncMock(return_value=iter(["Mocked", " AI", " response"]))
    base_deps_module._ai_chat_service = mock_ai_chat
    
    def override_get_ai_chat_service():
        return mock_ai_chat
    
    # === Mock MealGenerationService (uses AI - 3rd party) ===
    # Patch it in the infra.adapters module where it's imported from
    from src.infra.adapters.meal_generation_service import MealGenerationService as OriginalMealGen
    original_meal_gen_service = OriginalMealGen
    
    class MockMealGenerationService:
        """Mock meal generation service that returns predefined suggestions."""
        def __init__(self):
            """Initialize mock - no AI needed."""
            pass
        
        async def generate_meal(self, *args, **kwargs):
            """Return mock meal suggestion."""
            return {
                "suggestion_id": "suggestion-1",
                "name": "Grilled Chicken Salad",
                "calories": 450,
                "protein": 35.0,
                "carbs": 30.0,
                "fat": 20.0,
                "description": "Healthy grilled chicken salad",
                "estimated_cook_time_minutes": 20,
                "ingredients_list": ["Chicken", "Lettuce", "Tomato"],
                "instructions": ["Grill chicken", "Serve over salad"]
            }
        
        def generate_meal_plan(self, prompt, system_message, response_type="json", max_tokens=None, schema=None):
            """Return mock meal plan or meal names based on schema."""
            # Check if this is a MealNamesResponse request (has schema with meal_names)
            if schema and hasattr(schema, '__name__') and 'Name' in schema.__name__:
                # Return meal names as dict (service calls .get() on it)
                return {
                    "meal_names": [
                        "Grilled Chicken Salad",
                        "Quinoa Buddha Bowl", 
                        "Salmon with Vegetables",
                        "Turkey Wrap"
                    ]
                }
            elif schema and hasattr(schema, '__name__') and 'Recipe' in schema.__name__:
                # Return recipe details as dict with proper structure
                # Extract meal name from prompt if possible
                meal_name = "Grilled Chicken Salad"
                if "meal_name" in prompt.lower() or "name" in prompt.lower():
                    # Try to extract from prompt
                    import re
                    match = re.search(r'["\']([^"\']+)["\']', prompt)
                    if match:
                        meal_name = match.group(1)
                
                # Return format expected by RecipeDetailsResponse schema
                # The service calls .get() on this, so it must be a dict
                return {
                    "meal_name": meal_name,
                    "calories": 450,
                    "protein": 35.0,  # Service expects "protein" not "protein_g" 
                    "carbs": 30.0,
                    "fat": 20.0,
                    "prep_time_minutes": 20,
                    "ingredients": [
                        {"name": "Chicken Breast", "amount": 200.0, "unit": "g"},
                        {"name": "Lettuce", "amount": 100.0, "unit": "g"},
                        {"name": "Tomato", "amount": 50.0, "unit": "g"},
                        {"name": "Olive Oil", "amount": 15.0, "unit": "ml"}
                    ],
                    "recipe_steps": [
                        {"step": 1, "instruction": "Grill chicken breast for 6 minutes per side", "duration_minutes": 6},
                        {"step": 2, "instruction": "Chop lettuce and tomatoes", "duration_minutes": 5},
                        {"step": 3, "instruction": "Serve chicken over salad with olive oil dressing", "duration_minutes": 2}
                    ]
                }
            else:
                # Default response
                return {
                    "meals": [
                        {
                            "suggestion_id": "suggestion-1",
                            "name": "Grilled Chicken Salad",
                            "calories": 450,
                            "protein": 35.0,
                            "carbs": 30.0,
                            "fat": 20.0,
                            "description": "Healthy grilled chicken salad",
                            "estimated_cook_time_minutes": 20,
                            "ingredients_list": ["Chicken", "Lettuce", "Tomato"],
                            "instructions": ["Grill chicken", "Serve over salad"]
                        }
                    ]
                }
    
    # Patch in the module where it's imported
    import src.infra.adapters.meal_generation_service as meal_gen_module
    meal_gen_module.MealGenerationService = MockMealGenerationService
    
    # === FastAPI Dependency Overrides ===
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    
    def override_get_current_user_id():
        return "test_user_id"
    
    def override_get_cache_service():
        # Return the async mock cache
        return mock_cache
    
    def override_get_food_cache_service():
        mock_food_cache = Mock()
        mock_food_cache.get_cached_search = AsyncMock(return_value=None)
        mock_food_cache.cache_search = AsyncMock(return_value=None)
        mock_food_cache.get_cached_food = AsyncMock(return_value=None)
        mock_food_cache.cache_food = AsyncMock(return_value=None)
        return mock_food_cache
    
    # === Mock Food Data Service (USDA API - 3rd party) ===
    from src.domain.ports.food_data_service_port import FoodDataServicePort
    
    class MockFoodDataService(FoodDataServicePort):
        """Mock food data service that returns predefined food data."""
        async def get_food_details(self, fdc_id: int):
            """Return mock food details in USDA API format (details format)."""
            return {
                "fdcId": fdc_id,  # Handler expects camelCase
                "description": "Mock Food Item",
                "servingSize": 100.0,
                "servingSizeUnit": "g",
                "foodNutrients": [
                    {"nutrient": {"id": 1008}, "amount": 250.0},  # Calories - details format
                    {"nutrient": {"id": 1003}, "amount": 20.0},  # Protein
                    {"nutrient": {"id": 1005}, "amount": 30.0},  # Carbs
                    {"nutrient": {"id": 1004}, "amount": 10.0},  # Fat
                ]
            }
        
        async def get_multiple_foods(self, fdc_ids: list[int]):
            """Return mock food details for multiple IDs."""
            return [await self.get_food_details(fdc_id) for fdc_id in fdc_ids]
        
        async def search_foods(self, query: str, limit: int = 20):
            """Return mock search results."""
            return [
                {
                    "fdcId": 173944,
                    "description": "Chicken, breast, raw",
                    "dataType": "Foundation"
                }
            ]
    
    # Patch get_food_data_service to return our mock
    # This ensures the event bus uses the mock
    mock_food_data_service = MockFoodDataService()
    original_get_food_data_service = base_deps_module.get_food_data_service
    
    def patched_get_food_data_service():
        return mock_food_data_service
    
    base_deps_module.get_food_data_service = patched_get_food_data_service
    
    def override_get_food_data_service():
        return mock_food_data_service
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_food_cache_service] = override_get_food_cache_service
    app.dependency_overrides[get_food_data_service] = override_get_food_data_service
    app.dependency_overrides[get_ai_chat_service] = override_get_ai_chat_service
    
    client = TestClient(app)
    yield client
    
    # === Cleanup ===
    app.dependency_overrides.clear()
    UnitOfWork.__init__ = original_uow_init
    settings.CACHE_ENABLED = original_cache_enabled
    base_deps_module._redis_client = original_redis
    base_deps_module._cache_service = original_cache
    base_deps_module._image_store = None
    base_deps_module._vision_service = None
    base_deps_module._gpt_parser = None
    base_deps_module._ai_chat_service = None
    base_deps_module.get_food_data_service = original_get_food_data_service
    # Restore MealGenerationService
    import src.infra.adapters.meal_generation_service as meal_gen_module
    meal_gen_module.MealGenerationService = original_meal_gen_service
    db_config_module.SessionLocal = original_session_local
    db_config_module.ScopedSession = original_scoped_session
    event_bus_module._configured_event_bus = None


@pytest.fixture
def authenticated_client(api_client, test_user, test_session) -> TestClient:
    """
    API client with authenticated user.
    
    Uses test_user fixture and sets up authentication.
    """
    # Override get_current_user_id to return our test user ID
    def override_get_current_user_id():
        return test_user.id
    
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    
    yield api_client
    
    # Cleanup is handled by api_client fixture


@pytest.fixture
def test_user(test_session) -> User:
    """Create a test user in the database."""
    from uuid import uuid4
    from datetime import datetime
    
    user_id = str(uuid4())
    user = User(
        id=user_id,
        firebase_uid=f"test_firebase_{user_id[:8]}",
        email=f"test_{user_id[:8]}@example.com",
        username=f"testuser_{user_id[:8]}",
        password_hash="test_hash",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    test_session.add(user)
    test_session.flush()
    test_session.commit()
    return user


@pytest.fixture
def test_user_with_profile(test_session, test_user) -> tuple[User, UserProfile]:
    """Create a test user with profile."""
    from datetime import datetime
    
    profile = UserProfile(
        user_id=test_user.id,
        age=30,
        gender="male",
        height_cm=175,
        weight_kg=70,
        activity_level="moderate",
        fitness_goal="recomp",
        is_current=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    test_session.add(profile)
    test_session.flush()
    test_session.commit()
    return test_user, profile


@pytest.fixture
def mock_services():
    """
    Dictionary of mocked external services.
    
    Returns:
        dict: Contains mocks for vision_service, image_store, cache_service, etc.
    """
    mock_vision = MockVisionAIService()
    mock_image_store = Mock()
    mock_image_store.upload_image = AsyncMock(return_value="https://mock-image-url.com/image.jpg")
    mock_image_store.delete_image = AsyncMock(return_value=True)
    
    mock_cache = Mock()
    mock_cache.get = Mock(return_value=None)
    mock_cache.set = Mock(return_value=True)
    
    return {
        "vision_service": mock_vision,
        "image_store": mock_image_store,
        "cache_service": mock_cache,
    }


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Sample image bytes for testing."""
    # Return a minimal valid JPEG header
    # In real tests, you might want to use actual image files
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
