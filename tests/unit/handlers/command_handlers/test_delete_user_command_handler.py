"""
Unit tests for DeleteUserCommandHandler.
"""
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import DeleteUserCommand
from src.app.handlers.command_handlers.delete_user_command_handler import DeleteUserCommandHandler
from src.infra.database.config import Base
from src.infra.database.models.user import User


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def delete_handler():
    """Create a DeleteUserCommandHandler instance."""
    handler = DeleteUserCommandHandler()
    return handler


@pytest.fixture
def active_user(db_session):
    """Create an active user for testing."""
    user = User(
        email="activeuser@example.com",
        username="activeuser",
        password_hash="hashed_password",
        firebase_uid="firebase_active_123",
        first_name="Active",
        last_name="User",
        phone_number="+1234567890",
        display_name="Active User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session):
    """Create an inactive user for testing."""
    user = User(
        email="deleted_123@deleted.local",
        username="deleted_user_123",
        password_hash="DELETED",
        firebase_uid="firebase_deleted_123",
        is_active=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestDeleteUserCommandHandler:
    """Test suite for DeleteUserCommandHandler."""

    @pytest.mark.asyncio
    async def test_delete_active_user_successfully(self, delete_handler, active_user, db_session):
        """Test successfully deleting an active user."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=active_user.firebase_uid)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act
                result = await delete_handler.handle(command)

                # Assert
                assert result["firebase_uid"] == active_user.firebase_uid
                assert result["deleted"] is True
                assert result["message"] == "Account successfully deleted"

                # Verify user is soft deleted
                deleted_user = db_session.query(User).filter(
                    User.id == active_user.id
                ).first()
                assert deleted_user.is_active is False
                mock_firebase.assert_called_once_with(active_user.firebase_uid)

    @pytest.mark.asyncio
    async def test_anonymize_user_data_on_deletion(self, delete_handler, active_user, db_session):
        """Test that user data is anonymized during deletion."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=active_user.firebase_uid)
        user_id = active_user.id

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act
                await delete_handler.handle(command)

                # Assert - verify data anonymization
                deleted_user = db_session.query(User).filter(
                    User.id == user_id
                ).first()
                assert deleted_user.email == f"deleted_{user_id}@deleted.local"
                assert deleted_user.username == f"deleted_user_{user_id}"
                assert deleted_user.first_name is None
                assert deleted_user.last_name is None
                assert deleted_user.phone_number is None
                assert deleted_user.display_name is None
                assert deleted_user.photo_url is None
                assert deleted_user.password_hash == "DELETED"

    @pytest.mark.asyncio
    async def test_delete_inactive_user_raises_not_found(self, delete_handler, inactive_user, db_session):
        """Test that deleting an inactive user raises ResourceNotFoundException."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=inactive_user.firebase_uid)

        # Act & Assert
        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with pytest.raises(ResourceNotFoundException):
                await delete_handler.handle(command)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_raises_not_found(self, delete_handler, db_session):
        """Test that deleting a non-existent user raises ResourceNotFoundException."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid="nonexistent_firebase_uid")

        # Act & Assert
        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with pytest.raises(ResourceNotFoundException):
                await delete_handler.handle(command)

    @pytest.mark.asyncio
    async def test_firebase_deletion_failure_does_not_rollback_db(self, delete_handler, active_user, db_session):
        """Test that Firebase deletion failure doesn't rollback database changes."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=active_user.firebase_uid)
        user_id = active_user.id

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.side_effect = Exception("Firebase service unavailable")

                # Act
                result = await delete_handler.handle(command)

                # Assert - database changes should persist
                assert result["deleted"] is True
                deleted_user = db_session.query(User).filter(
                    User.id == user_id
                ).first()
                assert deleted_user.is_active is False
                assert deleted_user.email == f"deleted_{user_id}@deleted.local"

    @pytest.mark.asyncio
    async def test_missing_db_session_raises_runtime_error(self, delete_handler):
        """Test that missing database session raises RuntimeError."""
        # Arrange - mock ScopedSession to return None
        from src.infra.database.config import ScopedSession
        
        command = DeleteUserCommand(firebase_uid="some_uid")
        
        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=None)):
            # Act & Assert - should handle gracefully or raise appropriate error
            # Since ScopedSession is mocked to return None, handler will fail when trying to use db
            with pytest.raises((AttributeError, RuntimeError)):
                await delete_handler.handle(command)

    @pytest.mark.asyncio
    async def test_delete_user_preserves_user_id_in_anonymized_email(self, delete_handler, active_user, db_session):
        """Test that anonymized email preserves user ID for audit trail."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=active_user.firebase_uid)
        user_id = active_user.id

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act
                await delete_handler.handle(command)

                # Assert - verify user ID is in anonymized email for audit trail
                deleted_user = db_session.query(User).filter(
                    User.id == user_id
                ).first()
                assert str(user_id) in deleted_user.email
                assert str(user_id) in deleted_user.username

    @pytest.mark.asyncio
    async def test_delete_handles_exception_and_logs(self, delete_handler, active_user, db_session):
        """Test that exceptions are properly handled and logged."""
        from unittest.mock import patch
        from src.infra.database.config import ScopedSession
        
        # Arrange
        command = DeleteUserCommand(firebase_uid=active_user.firebase_uid)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            # Simulate unexpected database error
            mock_firebase.return_value = True
            
            # Mock ScopedSession to return a session with a failing commit
            mock_db = db_session
            original_commit = mock_db.commit
            
            def failing_commit():
                raise Exception("DB Error")
            
            mock_db.commit = failing_commit
            
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=mock_db)):
                # Act & Assert
                with pytest.raises(Exception, match="Failed to delete user account"):
                    await delete_handler.handle(command)


class TestDeleteUserCommandHandlerIntegration:
    """Integration tests for DeleteUserCommandHandler with actual database operations."""

    @pytest.mark.asyncio
    async def test_complete_deletion_flow(self, db_session):
        """Test complete user deletion flow with handler."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        user = User(
            email="integration_test@example.com",
            username="integration_test_user",
            password_hash="hashed_password",
            firebase_uid="firebase_integration_123",
            first_name="Integration",
            last_name="Test",
            phone_number="+1987654321",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        handler = DeleteUserCommandHandler()
        command = DeleteUserCommand(firebase_uid=user.firebase_uid)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act
                result = await handler.handle(command)

                # Assert result
                assert result["deleted"] is True

                # Assert database state
                db_user = db_session.query(User).filter(User.id == user.id).first()
                assert db_user.is_active is False
                assert "deleted_" in db_user.email
                assert db_user.password_hash == "DELETED"

    @pytest.mark.asyncio
    async def test_multiple_users_deletion_isolation(self, db_session):
        """Test that deleting one user doesn't affect other users."""
        from src.infra.database.config import ScopedSession
        
        # Arrange - create multiple users
        user1 = User(
            email="user1@example.com",
            username="user1",
            password_hash="pwd1",
            firebase_uid="firebase_1",
            is_active=True
        )
        user2 = User(
            email="user2@example.com",
            username="user2",
            password_hash="pwd2",
            firebase_uid="firebase_2",
            is_active=True
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        handler = DeleteUserCommandHandler()

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act - delete only user1
                await handler.handle(DeleteUserCommand(firebase_uid=user1.firebase_uid))

                # Assert
                db_user1 = db_session.query(User).filter(User.id == user1.id).first()
                db_user2 = db_session.query(User).filter(User.id == user2.id).first()

                assert db_user1.is_active is False
                assert db_user2.is_active is True
                assert db_user2.email == "user2@example.com"  # Unchanged

    @pytest.mark.asyncio
    async def test_soft_delete_preserves_historical_data_for_audit(self, db_session):
        """Test that soft delete preserves data for audit trail."""
        from src.infra.database.config import ScopedSession
        
        # Arrange
        user = User(
            email="audit_test@example.com",
            username="audit_user",
            password_hash="original_hash",
            firebase_uid="firebase_audit",
            first_name="Audit",
            last_name="Test",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        original_created = user.created_at
        original_id = user.id

        handler = DeleteUserCommandHandler()

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.ScopedSession', MagicMock(return_value=db_session)):
            with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
                mock_firebase.return_value = True

                # Act
                await handler.handle(DeleteUserCommand(firebase_uid=user.firebase_uid))

                # Assert - original ID and creation time preserved
                db_user = db_session.query(User).filter(User.id == original_id).first()
                assert db_user.id == original_id
                assert db_user.created_at == original_created
                assert db_user.is_active is False
