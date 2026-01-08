"""
Unit tests for SyncUserCommandHandler.
"""
from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from src.app.commands.user.sync_user_command import SyncUserCommand
from src.app.handlers.command_handlers.sync_user_command_handler import SyncUserCommandHandler
from src.infra.database.models.user import User


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def handler(mock_db_session):
    """Create a SyncUserCommandHandler instance."""
    handler = SyncUserCommandHandler()
    handler.set_dependencies(db=mock_db_session)
    return handler


class TestSyncUserCommandHandler:
    """Test suite for SyncUserCommandHandler."""

    @pytest.mark.asyncio
    async def test_handle_create_new_user(self, handler, mock_db_session):
        """Test creating a new user when no user exists."""
        command = SyncUserCommand(
            firebase_uid="firebase_123",
            email="newuser@example.com",
            phone_number="+1234567890",
            display_name="New User",
            photo_url="https://example.com/photo.jpg",
            provider="google",
            username="newuser",
            first_name="New",
            last_name="User"
        )
        
        # Mock query to return None (user doesn't exist)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        # Mock the created user
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.firebase_uid = "firebase_123"
        mock_user.email = "newuser@example.com"
        mock_user.username = "newuser"
        mock_user.first_name = "New"
        mock_user.last_name = "User"
        mock_user.phone_number = "+1234567890"
        mock_user.display_name = "New User"
        mock_user.photo_url = "https://example.com/photo.jpg"
        mock_user.provider = "google"
        mock_user.is_active = True
        mock_user.onboarding_completed = False
        mock_user.last_accessed = datetime.utcnow()
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        mock_user.is_premium.return_value = False
        mock_user.get_active_subscription.return_value = None
        
        # Mock refresh to return the user
        mock_db_session.refresh.return_value = None
        mock_db_session.add = Mock()
        mock_db_session.flush = Mock()
        mock_db_session.commit = Mock()
        
        # Set up the handler to use the mock user
        handler._create_new_user = Mock(return_value=mock_user)
        
        # Mock the notification preference creation to avoid actual database calls
        handler._create_default_notification_preferences_without_commit = Mock()
        
        result = await handler.handle(command)
        
        assert result["created"] is True
        assert result["updated"] is False
        assert result["user"]["firebase_uid"] == "firebase_123"
        assert result["user"]["email"] == "newuser@example.com"
        assert result["message"] == "User created successfully"
        # Verify flush was called to get user.id without committing
        mock_db_session.flush.assert_called_once()
        # Single atomic commit for both user and notification preferences
        mock_db_session.commit.assert_called_once()
        # Verify notification preferences were added to session for new user
        handler._create_default_notification_preferences_without_commit.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_handle_update_existing_user(self, handler, mock_db_session):
        """Test updating an existing user."""
        command = SyncUserCommand(
            firebase_uid="firebase_456",
            email="updated@example.com",
            phone_number="+1987654321",
            display_name="Updated User",
            photo_url="https://example.com/newphoto.jpg",
            provider="google",
            username="updateduser",
            first_name="Updated",
            last_name="User"
        )
        
        # Mock existing user
        mock_user = Mock(spec=User)
        mock_user.id = "user-456"
        mock_user.firebase_uid = "firebase_456"
        mock_user.email = "old@example.com"
        mock_user.username = "olduser"
        mock_user.first_name = "Old"
        mock_user.last_name = "User"
        mock_user.phone_number = "+1111111111"
        mock_user.display_name = "Old User"
        mock_user.photo_url = "https://example.com/oldphoto.jpg"
        mock_user.provider = "phone"
        mock_user.is_active = True
        mock_user.onboarding_completed = False
        mock_user.last_accessed = datetime.utcnow()
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        mock_user.is_premium.return_value = False
        mock_user.get_active_subscription.return_value = None
        
        # Mock query to return existing user
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db_session.query.return_value = mock_query
        
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        handler._update_existing_user = Mock(return_value=True)
        
        # Mock notification preferences (should NOT be called for existing users)
        handler._create_default_notification_preferences_without_commit = Mock()
        
        result = await handler.handle(command)
        
        assert result["created"] is False
        assert result["updated"] is True
        assert result["message"] == "User updated successfully"
        # For existing users, commit is only called once (no notification preferences creation)
        mock_db_session.commit.assert_called_once()
        # Verify notification preferences were NOT created for existing user
        handler._create_default_notification_preferences_without_commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_no_changes(self, handler, mock_db_session):
        """Test when user exists but no updates needed."""
        command = SyncUserCommand(
            firebase_uid="firebase_789",
            email="same@example.com",
            phone_number="+1234567890",
            display_name="Same User",
            photo_url="https://example.com/photo.jpg",
            provider="google"
        )
        
        # Mock existing user with same data
        mock_user = Mock(spec=User)
        mock_user.id = "user-789"
        mock_user.firebase_uid = "firebase_789"
        mock_user.email = "same@example.com"
        mock_user.phone_number = "+1234567890"
        mock_user.display_name = "Same User"
        mock_user.photo_url = "https://example.com/photo.jpg"
        mock_user.provider = "google"
        mock_user.is_active = True
        mock_user.onboarding_completed = False
        mock_user.last_accessed = datetime.utcnow()
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        mock_user.is_premium.return_value = False
        mock_user.get_active_subscription.return_value = None
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db_session.query.return_value = mock_query
        
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        # Simulate no changes
        handler._update_existing_user = Mock(return_value=True)  # last_accessed always updates
        
        result = await handler.handle(command)
        
        assert result["created"] is False
        assert result["message"] in ["User updated successfully", "User data up to date"]

    @pytest.mark.asyncio
    async def test_handle_with_premium_subscription(self, handler, mock_db_session):
        """Test syncing user with active premium subscription."""
        command = SyncUserCommand(
            firebase_uid="firebase_premium",
            email="premium@example.com",
            provider="google"
        )
        
        # Mock subscription
        mock_subscription = Mock()
        mock_subscription.product_id = "premium_monthly"
        mock_subscription.status = "active"
        mock_subscription.expires_at = datetime(2025, 12, 31)
        mock_subscription.platform = "ios"
        mock_subscription.is_monthly.return_value = True
        mock_subscription.is_yearly.return_value = False
        
        # Mock user with subscription
        mock_user = Mock(spec=User)
        mock_user.id = "user-premium"
        mock_user.firebase_uid = "firebase_premium"
        mock_user.email = "premium@example.com"
        mock_user.provider = "google"
        mock_user.is_active = True
        mock_user.onboarding_completed = True
        mock_user.last_accessed = datetime.utcnow()
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        mock_user.is_premium.return_value = True
        mock_user.get_active_subscription.return_value = mock_subscription
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db_session.query.return_value = mock_query
        
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        handler._update_existing_user = Mock(return_value=True)
        
        result = await handler.handle(command)
        
        assert result["user"]["is_premium"] is True
        assert result["user"]["subscription"] is not None
        assert result["user"]["subscription"]["product_id"] == "premium_monthly"
        assert result["user"]["subscription"]["is_monthly"] is True

    @pytest.mark.asyncio
    async def test_handle_database_error(self, handler, mock_db_session):
        """Test handling database error during sync."""
        command = SyncUserCommand(
            firebase_uid="firebase_error",
            email="error@example.com",
            provider="phone"
        )
        
        # Mock query to raise an exception
        mock_db_session.query.side_effect = Exception("Database error")
        mock_db_session.rollback = Mock()
        
        with pytest.raises(Exception, match="Database error"):
            await handler.handle(command)
        
        mock_db_session.rollback.assert_called_once()

    def test_generate_username_from_email(self, handler):
        """Test username generation from email."""
        username = handler._generate_username("john.doe@example.com", None)
        assert username == "johndoe"
        assert len(username) <= 20

    def test_generate_username_from_display_name(self, handler):
        """Test username generation from display name."""
        username = handler._generate_username("any@example.com", "John Doe")
        assert username == "johndoe"

    def test_generate_username_short(self, handler):
        """Test username generation for short names."""
        username = handler._generate_username("ab@example.com", None)
        assert username == "userab"
        assert len(username) >= 3

    def test_generate_username_long(self, handler):
        """Test username generation for very long names."""
        long_email = "verylongemailaddressfortesting@example.com"
        username = handler._generate_username(long_email, None)
        assert len(username) <= 20

    def test_generate_username_special_chars(self, handler):
        """Test username generation removes special characters."""
        username = handler._generate_username("john.doe+test@example.com", None)
        assert "." not in username
        assert "+" not in username

    def test_extract_names_from_full_name(self, handler):
        """Test extracting first and last names from display name."""
        first, last = handler._extract_names("John Doe", None, None)
        assert first == "John"
        assert last == "Doe"

    def test_extract_names_from_single_name(self, handler):
        """Test extracting names when only one name provided."""
        first, last = handler._extract_names("John", None, None)
        assert first == "John"
        assert last is None

    def test_extract_names_with_multiple_parts(self, handler):
        """Test extracting names from multi-part name."""
        first, last = handler._extract_names("John Paul Doe", None, None)
        assert first == "John"
        assert last == "Paul Doe"

    def test_extract_names_from_provided_names(self, handler):
        """Test using provided first and last names."""
        first, last = handler._extract_names(None, "Jane", "Smith")
        assert first == "Jane"
        assert last == "Smith"

    def test_extract_names_prefer_provided_over_display(self, handler):
        """Test that provided names take precedence over display name."""
        first, last = handler._extract_names("Wrong Name", "Correct", "Name")
        assert first == "Correct"
        assert last == "Name"

    @pytest.mark.asyncio
    async def test_handle_without_db_session(self):
        """Test error when handler has no database session."""
        handler = SyncUserCommandHandler()
        command = SyncUserCommand(
            firebase_uid="test",
            email="test@example.com",
            provider="google"
        )
        
        with pytest.raises(RuntimeError, match="Database session not configured"):
            await handler.handle(command)

