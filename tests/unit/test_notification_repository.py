"""
Unit tests for NotificationRepository.
"""
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from src.domain.model.notification import (
    UserFcmToken,
    NotificationPreferences,
    DeviceType
)
from src.infra.database.models.notification import (
    UserFcmToken as DBUserFcmToken,
    NotificationPreferences as DBNotificationPreferences
)
from src.infra.repositories.notification_repository import NotificationRepository

# Test UUIDs - using fixed UUIDs for consistency in tests
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_TOKEN_ID_1 = "00000000-0000-0000-0000-000000000011"
TEST_TOKEN_ID_2 = "00000000-0000-0000-0000-000000000012"
TEST_TOKEN_ID_123 = "00000000-0000-0000-0000-000000000123"


class TestNotificationRepository:
    """Tests for NotificationRepository."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        session.delete = Mock()
        return session
    
    @pytest.fixture
    def repository(self, mock_db_session):
        """Create repository with mock session."""
        return NotificationRepository(db=mock_db_session)
    
    # FCM Token Tests
    
    def test_save_new_fcm_token(self, repository, mock_db_session):
        """Test saving a new FCM token."""
        # Arrange
        token = UserFcmToken(
            token_id=TEST_TOKEN_ID_123,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-abc",
            device_type=DeviceType.IOS,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Mock query to return None (no existing token)
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Mock the database model to_domain
        with patch.object(DBUserFcmToken, 'to_domain', return_value=token):
            # Act
            result = repository.save_fcm_token(token)
            
            # Assert
            assert result.fcm_token == "fcm-token-abc"
            assert result.user_id == TEST_USER_ID
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_save_existing_fcm_token(self, repository, mock_db_session):
        """Test updating an existing FCM token."""
        # Arrange
        token = UserFcmToken(
            token_id=TEST_TOKEN_ID_123,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-abc",
            device_type=DeviceType.IOS,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Mock existing token
        existing_db_token = Mock(spec=DBUserFcmToken)
        existing_db_token.to_domain = Mock(return_value=token)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=existing_db_token)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.save_fcm_token(token)
        
        # Assert
        assert result.fcm_token == "fcm-token-abc"
        mock_db_session.add.assert_not_called()  # Should not add, only update
        mock_db_session.commit.assert_called_once()
        assert existing_db_token.user_id == TEST_USER_ID
        assert existing_db_token.device_type == "ios"
    
    def test_find_fcm_token_by_token_exists(self, repository, mock_db_session):
        """Test finding an FCM token that exists."""
        # Arrange
        token = UserFcmToken(
            token_id=TEST_TOKEN_ID_123,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-abc",
            device_type=DeviceType.IOS,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db_token = Mock(spec=DBUserFcmToken)
        db_token.to_domain = Mock(return_value=token)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_token)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_fcm_token_by_token("fcm-token-abc")
        
        # Assert
        assert result is not None
        assert result.fcm_token == "fcm-token-abc"
    
    def test_find_fcm_token_by_token_not_exists(self, repository, mock_db_session):
        """Test finding an FCM token that doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_fcm_token_by_token("non-existent-token")
        
        # Assert
        assert result is None
    
    def test_find_active_fcm_tokens_by_user(self, repository, mock_db_session):
        """Test finding all active FCM tokens for a user."""
        # Arrange
        token1 = UserFcmToken(
            token_id=TEST_TOKEN_ID_1,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-12345-1",
            device_type=DeviceType.IOS,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        token2 = UserFcmToken(
            token_id=TEST_TOKEN_ID_2,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-12345-2",
            device_type=DeviceType.ANDROID,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db_token1 = Mock(spec=DBUserFcmToken)
        db_token1.to_domain = Mock(return_value=token1)
        db_token2 = Mock(spec=DBUserFcmToken)
        db_token2.to_domain = Mock(return_value=token2)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[db_token1, db_token2])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_active_fcm_tokens_by_user(TEST_USER_ID)
        
        # Assert
        assert len(result) == 2
        assert result[0].fcm_token == "fcm-token-12345-1"
        assert result[1].fcm_token == "fcm-token-12345-2"
    
    def test_deactivate_fcm_token_exists(self, repository, mock_db_session):
        """Test deactivating an existing FCM token."""
        # Arrange
        db_token = Mock(spec=DBUserFcmToken)
        db_token.is_active = True
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_token)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.deactivate_fcm_token("fcm-token-abc")
        
        # Assert
        assert result is True
        assert db_token.is_active is False
        mock_db_session.commit.assert_called_once()
    
    def test_deactivate_fcm_token_not_exists(self, repository, mock_db_session):
        """Test deactivating a non-existent FCM token."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.deactivate_fcm_token("non-existent")
        
        # Assert
        assert result is False
        mock_db_session.commit.assert_not_called()
    
    def test_delete_fcm_token_exists(self, repository, mock_db_session):
        """Test deleting an existing FCM token."""
        # Arrange
        db_token = Mock(spec=DBUserFcmToken)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_token)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_fcm_token("fcm-token-abc")
        
        # Assert
        assert result is True
        mock_db_session.delete.assert_called_once_with(db_token)
        mock_db_session.commit.assert_called_once()
    
    def test_delete_fcm_token_not_exists(self, repository, mock_db_session):
        """Test deleting a non-existent FCM token."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_fcm_token("non-existent")
        
        # Assert
        assert result is False
        mock_db_session.delete.assert_not_called()
    
    # Notification Preferences Tests
    
    def test_save_new_notification_preferences(self, repository, mock_db_session):
        """Test saving new notification preferences."""
        # Arrange
        prefs = NotificationPreferences.create_default(TEST_USER_ID)
        
        # Mock query to return None (no existing preferences)
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Mock the database model to_domain
        with patch.object(DBNotificationPreferences, 'to_domain', return_value=prefs):
            # Act
            result = repository.save_notification_preferences(prefs)
            
            # Assert
            assert result.user_id == TEST_USER_ID
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_save_existing_notification_preferences(self, repository, mock_db_session):
        """Test updating existing notification preferences."""
        # Arrange
        prefs = NotificationPreferences.create_default(TEST_USER_ID)
        prefs.meal_reminders_enabled = False  # Changed value
        
        # Mock existing preferences
        existing_db_prefs = Mock(spec=DBNotificationPreferences)
        existing_db_prefs.to_domain = Mock(return_value=prefs)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=existing_db_prefs)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.save_notification_preferences(prefs)
        
        # Assert
        assert result.user_id == TEST_USER_ID
        mock_db_session.add.assert_not_called()  # Should not add, only update
        mock_db_session.commit.assert_called_once()
        assert existing_db_prefs.meal_reminders_enabled is False
    
    def test_find_notification_preferences_by_user_exists(self, repository, mock_db_session):
        """Test finding notification preferences that exist."""
        # Arrange
        prefs = NotificationPreferences.create_default(TEST_USER_ID)
        
        db_prefs = Mock(spec=DBNotificationPreferences)
        db_prefs.to_domain = Mock(return_value=prefs)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_prefs)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_notification_preferences_by_user(TEST_USER_ID)
        
        # Assert
        assert result is not None
        assert result.user_id == TEST_USER_ID
    
    def test_find_notification_preferences_by_user_not_exists(self, repository, mock_db_session):
        """Test finding notification preferences that don't exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_notification_preferences_by_user(TEST_USER_ID)
        
        # Assert
        assert result is None
    
    def test_update_notification_preferences(self, repository, mock_db_session):
        """Test updating notification preferences calls save_notification_preferences."""
        # Arrange
        prefs = NotificationPreferences.create_default(TEST_USER_ID)
        
        # Mock existing preferences
        existing_db_prefs = Mock(spec=DBNotificationPreferences)
        existing_db_prefs.to_domain = Mock(return_value=prefs)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=existing_db_prefs)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.update_notification_preferences(TEST_USER_ID, prefs)
        
        # Assert
        assert result.user_id == TEST_USER_ID
        mock_db_session.commit.assert_called_once()
    
    def test_delete_notification_preferences_exists(self, repository, mock_db_session):
        """Test deleting existing notification preferences."""
        # Arrange
        db_prefs = Mock(spec=DBNotificationPreferences)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_prefs)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_notification_preferences(TEST_USER_ID)
        
        # Assert
        assert result is True
        mock_db_session.delete.assert_called_once_with(db_prefs)
        mock_db_session.commit.assert_called_once()
    
    def test_delete_notification_preferences_not_exists(self, repository, mock_db_session):
        """Test deleting non-existent notification preferences."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_notification_preferences(TEST_USER_ID)
        
        # Assert
        assert result is False
        mock_db_session.delete.assert_not_called()
    
    # Utility Operations Tests

    def test_find_users_for_meal_reminder_breakfast(self, repository, mock_db_session):
        """Test finding users for breakfast reminder with timezone-aware query.

        Verifies the optimized query that includes time_field in initial query
        to avoid N+1 queries (no secondary query in loop).
        """
        # Arrange - mock returns tuples of (user_id, timezone, pref_minutes)
        # This is the optimized single-query pattern (no N+1)
        mock_query = Mock()
        mock_query.join = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        # Both users have breakfast at 480 minutes (8:00 AM)
        mock_query.all = Mock(return_value=[
            ("user-1", "UTC", 480),  # user_id, timezone, breakfast_time_minutes
            ("user-2", "UTC", 480)
        ])
        mock_db_session.query = Mock(return_value=mock_query)

        # Act - 8:00 UTC = 8:00 AM local time (480 minutes) for UTC users
        current_utc = datetime(2024, 12, 7, 8, 0, tzinfo=timezone.utc)
        result = repository.find_users_for_meal_reminder("breakfast", current_utc)

        # Assert - both users should match at 8:00 AM
        assert "user-1" in result
        assert "user-2" in result
        # Verify only ONE query was made (no N+1 - no secondary query.first calls)
        mock_db_session.query.assert_called_once()
    
    def test_find_users_for_meal_reminder_invalid_meal_type(self, repository, mock_db_session):
        """Test finding users for invalid meal type returns empty list."""
        # Act
        current_utc = datetime(2024, 12, 7, 8, 0, tzinfo=timezone.utc)
        result = repository.find_users_for_meal_reminder("invalid", current_utc)

        # Assert
        assert result == []
        mock_db_session.query.assert_not_called()
    
    def test_find_users_for_sleep_reminder(self, repository, mock_db_session):
        """Test finding users for sleep reminder with timezone-aware query."""
        # Arrange - mock returns tuples of (user_id, pref_minutes, timezone)
        mock_query = Mock()
        mock_query.join = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        # User with sleep time 22:00 (1320 minutes) in UTC timezone
        mock_query.all = Mock(return_value=[("user-1", 1320, "UTC")])
        mock_db_session.query = Mock(return_value=mock_query)

        # Act - 22:00 UTC = 22:00 local time for UTC user
        current_utc = datetime(2024, 12, 7, 22, 0, tzinfo=timezone.utc)
        result = repository.find_users_for_sleep_reminder(current_utc)

        # Assert
        assert len(result) == 1
        assert "user-1" in result
    
    # Error Handling Tests
    
    def test_save_fcm_token_error_rollback(self, repository, mock_db_session):
        """Test that errors during save trigger rollback."""
        # Arrange
        token = UserFcmToken(
            token_id=TEST_TOKEN_ID_123,
            user_id=TEST_USER_ID,
            fcm_token="fcm-token-abc",
            device_type=DeviceType.IOS,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.save_fcm_token(token)
        
        mock_db_session.rollback.assert_called_once()
    
    def test_save_notification_preferences_error_rollback(self, repository, mock_db_session):
        """Test that errors during save trigger rollback."""
        # Arrange
        prefs = NotificationPreferences.create_default(TEST_USER_ID)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.save_notification_preferences(prefs)
        
        mock_db_session.rollback.assert_called_once()
    
    def test_delete_notification_preferences_error_rollback(self, repository, mock_db_session):
        """Test that errors during delete trigger rollback."""
        # Arrange
        db_prefs = Mock(spec=DBNotificationPreferences)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_prefs)
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.delete_notification_preferences(TEST_USER_ID)
        
        mock_db_session.rollback.assert_called_once()
    
    # Session Management Tests
    
    def test_repository_without_session_creates_and_closes(self):
        """Test repository creates and closes session when not provided."""
        # Arrange
        # Patch SessionLocal in the repository module's namespace since it's imported at module level
        with patch('src.infra.repositories.notification_repository.SessionLocal') as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            mock_query = Mock()
            mock_query.filter = Mock(return_value=mock_query)
            mock_query.first = Mock(return_value=None)
            mock_session.query = Mock(return_value=mock_query)
            
            repository = NotificationRepository(db=None)
            
            # Act
            result = repository.find_fcm_token_by_token("test-token")
            
            # Assert
            mock_session_local.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_repository_with_session_does_not_close(self, repository, mock_db_session):
        """Test repository does not close session when provided."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_fcm_token_by_token("test-token")
        
        # Assert
        mock_db_session.close.assert_not_called()

