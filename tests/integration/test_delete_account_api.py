"""
Integration tests for delete account API endpoint.
Tests the complete flow from API request to database changes.
"""
from unittest.mock import patch
from firebase_admin.auth import UserNotFoundError
import pytest

from src.infra.database.models.user import User
from src.app.commands.user import DeleteUserCommand


@pytest.mark.integration
class TestDeleteAccountIntegration:
    """Integration tests for complete delete account workflow."""

    @pytest.mark.asyncio
    async def test_delete_account_complete_flow(self, test_session, event_bus):
        """Test complete user deletion flow."""
        # Arrange - create a test user
        user = User(
            email="integration_test@example.com",
            username="integration_user",
            password_hash="hashed_password",
            firebase_uid="firebase_integration_123",
            first_name="Integration",
            last_name="Test",
            phone_number="+1234567890",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        # Verify user is active
        active_user = test_session.query(User).filter(
            User.firebase_uid == "firebase_integration_123",
            User.is_active == True
        ).first()
        assert active_user is not None
        assert active_user.email == "integration_test@example.com"

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.return_value = True

            # Act - execute delete command
            command = DeleteUserCommand(firebase_uid="firebase_integration_123")
            result = await event_bus.send(command)

            # Assert
            assert result["deleted"] is True
            assert result["firebase_uid"] == "firebase_integration_123"

            # Verify user is now inactive
            deleted_user = test_session.query(User).filter(
                User.id == user.id
            ).first()
            assert deleted_user.is_active is False
            assert "deleted_" in deleted_user.email

            # Verify user cannot be found by active query
            cannot_find = test_session.query(User).filter(
                User.firebase_uid == "firebase_integration_123",
                User.is_active == True
            ).first()
            assert cannot_find is None

    @pytest.mark.asyncio
    async def test_delete_user_data_anonymization(self, test_session, event_bus):
        """Test that user data is properly anonymized."""
        # Arrange
        user = User(
            email="anonymize_test@example.com",
            username="anonymize_user",
            password_hash="original_hash",
            firebase_uid="firebase_anon_123",
            first_name="Original",
            last_name="Name",
            phone_number="+1987654321",
            display_name="Test User",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        user_id = user.id

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.return_value = True

            # Act
            command = DeleteUserCommand(firebase_uid="firebase_anon_123")
            result = await event_bus.send(command)

            # Assert
            assert result["deleted"] is True

            # Verify anonymization
            deleted_user = test_session.query(User).filter(User.id == user_id).first()
            assert deleted_user.email == f"deleted_{user_id}@deleted.local"
            assert deleted_user.username == f"deleted_user_{user_id}"
            assert deleted_user.first_name is None
            assert deleted_user.last_name is None
            assert deleted_user.phone_number is None
            assert deleted_user.display_name is None
            assert deleted_user.password_hash == "DELETED"

    @pytest.mark.asyncio
    async def test_multiple_users_deletion_isolation(self, test_session, event_bus):
        """Test that deleting one user doesn't affect others."""
        # Arrange - create two users
        user1 = User(
            email="user1_integration@example.com",
            username="user1_int",
            password_hash="pwd1",
            firebase_uid="firebase_user1_int",
            is_active=True
        )
        user2 = User(
            email="user2_integration@example.com",
            username="user2_int",
            password_hash="pwd2",
            firebase_uid="firebase_user2_int",
            is_active=True
        )
        test_session.add_all([user1, user2])
        test_session.commit()
        test_session.refresh(user1)
        test_session.refresh(user2)

        user1_id = user1.id
        user2_id = user2.id

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.return_value = True

            # Act - delete only user1
            command = DeleteUserCommand(firebase_uid="firebase_user1_int")
            result = await event_bus.send(command)
            assert result["deleted"] is True

            # Assert
            deleted_user1 = test_session.query(User).filter(User.id == user1_id).first()
            unaffected_user2 = test_session.query(User).filter(User.id == user2_id).first()

            assert deleted_user1.is_active is False
            assert unaffected_user2.is_active is True
            assert unaffected_user2.email == "user2_integration@example.com"

    @pytest.mark.asyncio
    async def test_delete_preserves_audit_trail(self, test_session, event_bus):
        """Test that soft delete preserves data for audit trail."""
        # Arrange
        user = User(
            email="audit_integration@example.com",
            username="audit_user_int",
            password_hash="hash",
            firebase_uid="firebase_audit_int",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        original_id = user.id
        original_created = user.created_at

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.return_value = True

            # Act
            command = DeleteUserCommand(firebase_uid="firebase_audit_int")
            await event_bus.send(command)

            # Assert - ID and creation time preserved
            deleted_user = test_session.query(User).filter(User.id == original_id).first()
            assert deleted_user.id == original_id
            assert deleted_user.created_at == original_created
            assert deleted_user.is_active is False

    @pytest.mark.asyncio
    async def test_firebase_failure_does_not_prevent_soft_delete(self, test_session, event_bus):
        """Test that database soft delete succeeds even if Firebase deletion fails."""
        # Arrange
        user = User(
            email="firebase_fail_test@example.com",
            username="firebase_fail_user",
            password_hash="hash",
            firebase_uid="firebase_fail_int",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.side_effect = Exception("Firebase unavailable")

            # Act
            command = DeleteUserCommand(firebase_uid="firebase_fail_int")
            result = await event_bus.send(command)

            # Assert - should still return deleted=True
            assert result["deleted"] is True

            # Verify soft delete persisted
            deleted_user = test_session.query(User).filter(User.id == user.id).first()
            assert deleted_user.is_active is False
            assert "deleted_" in deleted_user.email

    @pytest.mark.asyncio
    async def test_deleted_user_filtered_from_queries(self, test_session, event_bus):
        """Test that deleted users are properly filtered from active queries."""
        # Arrange - create a user and delete it
        user = User(
            email="filter_test@example.com",
            username="filter_user",
            password_hash="hash",
            firebase_uid="firebase_filter_int",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            mock_firebase.return_value = True

            # Act - delete user
            command = DeleteUserCommand(firebase_uid="firebase_filter_int")
            await event_bus.send(command)

            # Assert - simulate auth check (only find active users)
            active_user = test_session.query(User).filter(
                User.firebase_uid == "firebase_filter_int",
                User.is_active == True
            ).first()
            assert active_user is None

            # But deleted user still exists in database
            all_user = test_session.query(User).filter(
                User.firebase_uid == "firebase_filter_int"
            ).first()
            assert all_user is not None
            assert all_user.is_active is False

    @pytest.mark.asyncio
    async def test_idempotent_firebase_deletion(self, test_session, event_bus):
        """Test that firebase deletion failures are handled gracefully."""
        # Arrange
        user = User(
            email="idem_test@example.com",
            username="idem_user",
            password_hash="hash",
            firebase_uid="firebase_idem_int",
            is_active=True
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        with patch('src.app.handlers.command_handlers.delete_user_command_handler.FirebaseAuthService.delete_firebase_user') as mock_firebase:
            # Simulate Firebase not found (already deleted)
            mock_firebase.side_effect = UserNotFoundError("User not found in Firebase")

            # Act & Assert - should not crash
            command = DeleteUserCommand(firebase_uid="firebase_idem_int")
            result = await event_bus.send(command)

            assert result["deleted"] is True
