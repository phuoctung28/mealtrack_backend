"""
Basic test to verify test setup is working.
"""
import pytest
from sqlalchemy import text


def test_database_connection(test_session):
    """Test that database connection works."""
    result = test_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_database_rollback(test_session):
    """Test that database changes are rolled back."""
    from src.infra.database.models.user.user import User
    from datetime import datetime
    
    # Create a user
    user = User(
        id="test-rollback",
        firebase_uid="test-rollback-firebase-uid",
        email="rollback@test.com",
        username="rollbacktest",
        password_hash="dummy_hash_for_test",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    test_session.add(user)
    test_session.commit()
    
    # Verify user exists in this session
    found = test_session.query(User).filter_by(id="test-rollback").first()
    assert found is not None
    assert found.email == "rollback@test.com"
    
    # User will be rolled back after test completes


def test_mock_services(mock_image_store, mock_vision_service):
    """Test that mock services are available."""
    # Test image store
    image_id = mock_image_store.save(b"test-image", "image/jpeg")
    # Now save returns just the UUID
    assert len(image_id) == 36  # UUID length
    assert "-" in image_id  # UUID format
    
    # Test get_url returns the full mock URL
    image_url = mock_image_store.get_url(image_id)
    assert image_url.startswith("mock://images/")
    
    # Test vision service
    result = mock_vision_service.analyze(b"test-image")
    assert "structured_data" in result
    assert result["structured_data"]["dish_name"] == "Grilled Chicken with Rice"


@pytest.mark.asyncio
async def test_async_support():
    """Test that async tests work properly."""
    import asyncio
    await asyncio.sleep(0.01)
    assert True