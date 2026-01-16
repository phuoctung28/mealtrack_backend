"""
Unit tests for SyncUserCommandHandler using FakeUnitOfWork.
This proves the handlers are decoupled from infrastructure.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from src.app.commands.user.sync_user_command import SyncUserCommand
from src.app.handlers.command_handlers.sync_user_command_handler import SyncUserCommandHandler
from tests.fixtures.fakes.fake_uow import FakeUnitOfWork
from src.domain.model.auth.auth_provider import AuthProvider

@pytest.mark.asyncio
async def test_sync_user_creates_new_user_with_fake_uow():
    # Arrange
    fake_uow = FakeUnitOfWork()
    handler = SyncUserCommandHandler(uow=fake_uow)
    
    command = SyncUserCommand(
        firebase_uid="firebase_123",
        email="test@example.com",
        display_name="Test User",
        provider="google"
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result["created"] is True
    assert result["user"]["email"] == "test@example.com"
    
    # Verify persistence in fake repo
    user_in_repo = fake_uow.users.find_by_firebase_uid("firebase_123")
    assert user_in_repo is not None
    assert user_in_repo.username == "testuser" # Logic from _generate_username
    assert fake_uow.committed is True

@pytest.mark.asyncio
async def test_sync_user_updates_existing_user_with_fake_uow():
    # Arrange
    fake_uow = FakeUnitOfWork()
    
    # Pre-populate user
    from src.domain.model.user import UserDomainModel
    existing_user = UserDomainModel(
        firebase_uid="firebase_123",
        email="old@example.com",
        username="existinguser",
        password_hash="",
        provider=AuthProvider.GOOGLE
    )
    fake_uow.users.save(existing_user)
    
    handler = SyncUserCommandHandler(uow=fake_uow)
    
    command = SyncUserCommand(
        firebase_uid="firebase_123",
        email="new@example.com", # Changed email
        display_name="Existing User",
        provider="google"
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result["updated"] is True
    assert result["user"]["email"] == "new@example.com"
    
    # Verify update in repo
    updated_user = fake_uow.users.find_by_firebase_uid("firebase_123")
    assert updated_user.email == "new@example.com"
    assert fake_uow.committed is True
