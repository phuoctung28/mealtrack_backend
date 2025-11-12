"""
Unit tests for ChatRepository.
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.domain.model.chat import (
    Thread,
    Message,
    MessageRole,
    ThreadStatus
)
from src.infra.repositories.chat_repository import ChatRepository
from src.infra.database.models.chat import (
    ChatThread as DBChatThread,
    ChatMessage as DBChatMessage
)

# Test UUIDs - using fixed UUIDs for consistency in tests
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_THREAD_ID = "00000000-0000-0000-0000-000000000002"


class TestChatRepository:
    """Tests for ChatRepository."""
    
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
        session.refresh = Mock()
        return session
    
    @pytest.fixture
    def repository(self, mock_db_session):
        """Create repository with mock session."""
        return ChatRepository(db=mock_db_session)
    
    # Thread Tests
    
    def test_save_new_thread(self, repository, mock_db_session):
        """Test saving a new thread."""
        # Arrange
        thread = Thread.create_new(
            user_id=TEST_USER_ID,
            title="Test Thread",
            metadata={"key": "value"}
        )
        
        # Mock query to return None (no existing thread)
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Mock the database model to_domain
        with patch.object(DBChatThread, 'to_domain', return_value=thread):
            # Act
            result = repository.save_thread(thread)
            
            # Assert
            assert result.thread_id == thread.thread_id
            assert result.title == "Test Thread"
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
    
    def test_save_existing_thread(self, repository, mock_db_session):
        """Test updating an existing thread."""
        # Arrange
        thread = Thread.create_new(
            user_id=TEST_USER_ID,
            title="Updated Title"
        )
        
        # Mock existing thread
        existing_db_thread = Mock(spec=DBChatThread)
        existing_db_thread.to_domain = Mock(return_value=thread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=existing_db_thread)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.save_thread(thread)
        
        # Assert
        assert result.title == "Updated Title"
        mock_db_session.add.assert_not_called()  # Should not add, only update
        mock_db_session.commit.assert_called_once()
        assert existing_db_thread.title == "Updated Title"
        assert existing_db_thread.status == "active"
    
    def test_find_thread_by_id_exists(self, repository, mock_db_session):
        """Test finding a thread that exists."""
        # Arrange
        thread = Thread.create_new(user_id=TEST_USER_ID, title="Test")
        
        db_thread = Mock(spec=DBChatThread)
        db_thread.to_domain = Mock(return_value=thread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_thread)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_thread_by_id(thread.thread_id)
        
        # Assert
        assert result is not None
        assert result.thread_id == thread.thread_id
    
    def test_find_thread_by_id_not_exists(self, repository, mock_db_session):
        """Test finding a thread that doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_thread_by_id("non-existent")
        
        # Assert
        assert result is None
    
    def test_find_threads_by_user(self, repository, mock_db_session):
        """Test finding all threads for a user."""
        # Arrange
        thread1 = Thread.create_new(user_id=TEST_USER_ID, title="Thread 1")
        thread2 = Thread.create_new(user_id=TEST_USER_ID, title="Thread 2")
        
        db_thread1 = Mock(spec=DBChatThread)
        db_thread1.to_domain = Mock(return_value=thread1)
        db_thread2 = Mock(spec=DBChatThread)
        db_thread2.to_domain = Mock(return_value=thread2)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[db_thread1, db_thread2])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_threads_by_user(TEST_USER_ID, limit=50, offset=0)
        
        # Assert
        assert len(result) == 2
        assert result[0].title == "Thread 1"
        assert result[1].title == "Thread 2"
    
    def test_find_threads_by_user_exclude_deleted(self, repository, mock_db_session):
        """Test finding threads excludes deleted by default."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_threads_by_user(TEST_USER_ID, include_deleted=False)
        
        # Assert
        # Verify filter was called twice (user_id and status != 'deleted')
        assert mock_query.filter.call_count == 2
    
    def test_delete_thread_exists(self, repository, mock_db_session):
        """Test deleting an existing thread."""
        # Arrange
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_thread)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_thread(TEST_THREAD_ID)
        
        # Assert
        assert result is True
        assert db_thread.status == 'deleted'
        assert db_thread.is_active is False
        mock_db_session.commit.assert_called_once()
    
    def test_delete_thread_not_exists(self, repository, mock_db_session):
        """Test deleting a non-existent thread."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.delete_thread("non-existent")
        
        # Assert
        assert result is False
        mock_db_session.commit.assert_not_called()
    
    # Message Tests
    
    def test_save_new_message(self, repository, mock_db_session):
        """Test saving a new message."""
        # Arrange
        message = Message.create_user_message(
            thread_id=TEST_THREAD_ID,
            content="Hello!",
            metadata={"key": "value"}
        )
        
        # Mock query to return None (no existing message)
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        
        # First query for message, second for thread update
        db_thread = Mock(spec=DBChatThread)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Mock the database model to_domain
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            result = repository.save_message(message)
            
            # Assert
            assert result.content == "Hello!"
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
    
    def test_save_existing_message(self, repository, mock_db_session):
        """Test updating an existing message."""
        # Arrange
        message = Message.create_user_message(
            thread_id=TEST_THREAD_ID,
            content="Updated content"
        )
        
        # Mock existing message
        existing_db_message = Mock(spec=DBChatMessage)
        existing_db_message.to_domain = Mock(return_value=message)
        
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[existing_db_message, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.save_message(message)
        
        # Assert
        assert result.content == "Updated content"
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()
        assert existing_db_message.content == "Updated content"
    
    def test_save_message_updates_thread_timestamp(self, repository, mock_db_session):
        """Test that saving a message updates the thread's updated_at."""
        # Arrange
        message = Message.create_user_message(
            thread_id=TEST_THREAD_ID,
            content="Hello!"
        )
        
        db_thread = Mock(spec=DBChatThread)
        original_time = db_thread.updated_at
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            repository.save_message(message)
            
            # Assert
            assert db_thread.updated_at != original_time
    
    def test_find_messages_by_thread(self, repository, mock_db_session):
        """Test finding all messages for a thread."""
        # Arrange
        msg1 = Message.create_user_message(thread_id=TEST_THREAD_ID, content="First")
        msg2 = Message.create_assistant_message(thread_id=TEST_THREAD_ID, content="Second")
        
        db_msg1 = Mock(spec=DBChatMessage)
        db_msg1.to_domain = Mock(return_value=msg1)
        db_msg2 = Mock(spec=DBChatMessage)
        db_msg2.to_domain = Mock(return_value=msg2)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[db_msg1, db_msg2])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_messages_by_thread(TEST_THREAD_ID, limit=100, offset=0)
        
        # Assert
        assert len(result) == 2
        assert result[0].content == "First"
        assert result[1].content == "Second"
    
    def test_find_messages_by_thread_with_pagination(self, repository, mock_db_session):
        """Test finding messages with pagination."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_messages_by_thread(TEST_THREAD_ID, limit=50, offset=10)
        
        # Assert
        mock_query.limit.assert_called_once_with(50)
        mock_query.offset.assert_called_once_with(10)
    
    # Count Tests
    
    def test_count_user_threads(self, repository, mock_db_session):
        """Test counting user threads."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.scalar = Mock(return_value=5)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.count_user_threads(TEST_USER_ID, include_deleted=False)
        
        # Assert
        assert result == 5
        # Verify filter called for user_id and status
        assert mock_query.filter.call_count == 2
    
    def test_count_user_threads_include_deleted(self, repository, mock_db_session):
        """Test counting user threads including deleted."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.scalar = Mock(return_value=8)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.count_user_threads(TEST_USER_ID, include_deleted=True)
        
        # Assert
        assert result == 8
        # Verify filter only called once (user_id only)
        assert mock_query.filter.call_count == 1
    
    def test_count_user_threads_returns_zero_when_none(self, repository, mock_db_session):
        """Test count returns 0 when scalar returns None."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.scalar = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.count_user_threads(TEST_USER_ID)
        
        # Assert
        assert result == 0
    
    def test_count_thread_messages(self, repository, mock_db_session):
        """Test counting messages in a thread."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.scalar = Mock(return_value=10)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.count_thread_messages(TEST_THREAD_ID)
        
        # Assert
        assert result == 10
    
    def test_count_thread_messages_returns_zero_when_none(self, repository, mock_db_session):
        """Test count returns 0 when scalar returns None."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.scalar = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.count_thread_messages(TEST_THREAD_ID)
        
        # Assert
        assert result == 0
    
    # Error Handling Tests
    
    def test_save_thread_error_rollback(self, repository, mock_db_session):
        """Test that errors during save trigger rollback."""
        # Arrange
        thread = Thread.create_new(user_id=TEST_USER_ID)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.save_thread(thread)
        
        mock_db_session.rollback.assert_called_once()
    
    def test_save_message_error_rollback(self, repository, mock_db_session):
        """Test that errors during message save trigger rollback."""
        # Arrange
        message = Message.create_user_message(
            thread_id=TEST_THREAD_ID,
            content="Test"
        )
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, None])
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.save_message(message)
        
        mock_db_session.rollback.assert_called_once()
    
    def test_delete_thread_error_rollback(self, repository, mock_db_session):
        """Test that errors during delete trigger rollback."""
        # Arrange
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=db_thread)
        mock_db_session.query = Mock(return_value=mock_query)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            repository.delete_thread(TEST_THREAD_ID)
        
        mock_db_session.rollback.assert_called_once()
    
    # Session Management Tests
    
    def test_repository_without_session_creates_and_closes(self):
        """Test repository creates and closes session when not provided."""
        # Arrange
        with patch('src.infra.database.config.SessionLocal') as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            mock_query = Mock()
            mock_query.filter = Mock(return_value=mock_query)
            mock_query.first = Mock(return_value=None)
            mock_session.query = Mock(return_value=mock_query)
            
            repository = ChatRepository(db=None)
            
            # Act
            result = repository.find_thread_by_id("test-thread")
            
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
        result = repository.find_thread_by_id("test-thread")
        
        # Assert
        mock_db_session.close.assert_not_called()
    
    # Thread Status Tests
    
    def test_save_archived_thread(self, repository, mock_db_session):
        """Test saving an archived thread."""
        # Arrange
        thread = Thread.create_new(user_id=TEST_USER_ID)
        archived_thread = thread.archive()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatThread, 'to_domain', return_value=archived_thread):
            # Act
            result = repository.save_thread(archived_thread)
            
            # Assert
            assert result.status == ThreadStatus.ARCHIVED
    
    def test_save_deleted_thread(self, repository, mock_db_session):
        """Test saving a deleted thread."""
        # Arrange
        thread = Thread.create_new(user_id=TEST_USER_ID)
        deleted_thread = thread.delete()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatThread, 'to_domain', return_value=deleted_thread):
            # Act
            result = repository.save_thread(deleted_thread)
            
            # Assert
            assert result.status == ThreadStatus.DELETED
    
    # Message Role Tests
    
    def test_save_user_message(self, repository, mock_db_session):
        """Test saving a user message."""
        # Arrange
        message = Message.create_user_message(thread_id=TEST_THREAD_ID, content="User says hi")
        
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            result = repository.save_message(message)
            
            # Assert
            assert result.role == MessageRole.USER
    
    def test_save_assistant_message(self, repository, mock_db_session):
        """Test saving an assistant message."""
        # Arrange
        message = Message.create_assistant_message(thread_id=TEST_THREAD_ID, content="AI responds")
        
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            result = repository.save_message(message)
            
            # Assert
            assert result.role == MessageRole.ASSISTANT
    
    def test_save_system_message(self, repository, mock_db_session):
        """Test saving a system message."""
        # Arrange
        message = Message.create_system_message(thread_id=TEST_THREAD_ID, content="System message")
        
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            result = repository.save_message(message)
            
            # Assert
            assert result.role == MessageRole.SYSTEM
    
    # Metadata Handling Tests
    
    def test_save_thread_with_metadata(self, repository, mock_db_session):
        """Test saving thread with metadata."""
        # Arrange
        thread = Thread.create_new(
            user_id=TEST_USER_ID,
            metadata={"context": "nutrition", "tags": ["protein", "diet"]}
        )
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatThread, 'to_domain', return_value=thread):
            # Act
            result = repository.save_thread(thread)
            
            # Assert
            assert result.metadata is not None
            assert result.metadata["context"] == "nutrition"
    
    def test_save_message_with_metadata(self, repository, mock_db_session):
        """Test saving message with metadata."""
        # Arrange
        message = Message.create_assistant_message(
            thread_id=TEST_THREAD_ID,
            content="Response",
            metadata={"model": "gpt-4", "tokens": 150}
        )
        
        db_thread = Mock(spec=DBChatThread)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, db_thread])
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act
            result = repository.save_message(message)
            
            # Assert
            assert result.metadata is not None
            assert result.metadata["model"] == "gpt-4"
            assert result.metadata["tokens"] == 150
    
    # Edge Cases
    
    def test_find_threads_by_user_empty_result(self, repository, mock_db_session):
        """Test finding threads when user has none."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_threads_by_user(TEST_USER_ID)
        
        # Assert
        assert result == []
    
    def test_find_messages_by_thread_empty_result(self, repository, mock_db_session):
        """Test finding messages when thread is empty."""
        # Arrange
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Act
        result = repository.find_messages_by_thread(TEST_THREAD_ID)
        
        # Assert
        assert result == []
    
    def test_save_thread_with_no_metadata(self, repository, mock_db_session):
        """Test saving thread without metadata."""
        # Arrange
        thread = Thread.create_new(user_id=TEST_USER_ID, metadata=None)
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatThread, 'to_domain', return_value=thread):
            # Act
            result = repository.save_thread(thread)
            
            # Assert
            # Should not raise error
            assert result is not None
    
    def test_save_message_no_thread_found(self, repository, mock_db_session):
        """Test saving message when thread doesn't exist."""
        # Arrange
        message = Message.create_user_message(thread_id=TEST_THREAD_ID, content="Hello")
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(side_effect=[None, None])  # No message, no thread
        mock_db_session.query = Mock(return_value=mock_query)
        
        with patch.object(DBChatMessage, 'to_domain', return_value=message):
            # Act - should still save message but not update thread
            result = repository.save_message(message)
            
            # Assert
            assert result.message_id == message.message_id
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()

