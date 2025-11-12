"""
Unit tests for chat domain models.
"""
import pytest
from datetime import datetime

from src.domain.model.chat import Thread, Message, MessageRole, ThreadStatus


class TestMessage:
    """Tests for Message domain model."""
    
    def test_create_user_message(self):
        """Test creating a user message."""
        thread_id = "123e4567-e89b-12d3-a456-426614174000"
        content = "Hello, can you help me?"
        
        message = Message.create_user_message(thread_id=thread_id, content=content)
        
        assert message.thread_id == thread_id
        assert message.content == content
        assert message.role == MessageRole.USER
        assert message.message_id is not None
        assert isinstance(message.created_at, datetime)
    
    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        thread_id = "123e4567-e89b-12d3-a456-426614174000"
        content = "Of course! How can I help?"
        
        message = Message.create_assistant_message(thread_id=thread_id, content=content)
        
        assert message.thread_id == thread_id
        assert message.content == content
        assert message.role == MessageRole.ASSISTANT
    
    def test_empty_content_raises_error(self):
        """Test that empty content raises ValueError."""
        thread_id = "123e4567-e89b-12d3-a456-426614174000"
        
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            Message.create_user_message(thread_id=thread_id, content="")
    
    def test_content_too_long_raises_error(self):
        """Test that content over limit raises ValueError."""
        thread_id = "123e4567-e89b-12d3-a456-426614174000"
        content = "x" * 50001  # Over 50000 limit
        
        with pytest.raises(ValueError, match="Message content too long"):
            Message.create_user_message(thread_id=thread_id, content=content)
    
    def test_message_to_dict(self):
        """Test message to_dict conversion."""
        thread_id = "123e4567-e89b-12d3-a456-426614174000"
        message = Message.create_user_message(thread_id=thread_id, content="Test")
        
        result = message.to_dict()
        
        assert result["thread_id"] == thread_id
        assert result["content"] == "Test"
        assert result["role"] == "user"
        assert "message_id" in result
        assert "created_at" in result


class TestThread:
    """Tests for Thread domain model."""
    
    def test_create_new_thread(self):
        """Test creating a new thread."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        title = "Nutrition Questions"
        
        thread = Thread.create_new(user_id=user_id, title=title)
        
        assert thread.user_id == user_id
        assert thread.title == title
        assert thread.status == ThreadStatus.ACTIVE
        assert thread.thread_id is not None
        assert len(thread.messages) == 0
    
    def test_add_message_to_thread(self):
        """Test adding a message to a thread."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        message = Message.create_user_message(thread_id=thread.thread_id, content="Test")
        
        updated_thread = thread.add_message(message)
        
        assert len(updated_thread.messages) == 1
        assert updated_thread.messages[0].content == "Test"
        assert updated_thread.get_message_count() == 1
    
    def test_add_message_wrong_thread_raises_error(self):
        """Test that adding message from different thread raises error."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        wrong_thread_id = "223e4567-e89b-12d3-a456-426614174000"
        message = Message.create_user_message(thread_id=wrong_thread_id, content="Test")
        
        with pytest.raises(ValueError, match="does not match thread"):
            thread.add_message(message)
    
    def test_archive_thread(self):
        """Test archiving a thread."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        
        archived = thread.archive()
        
        assert archived.status == ThreadStatus.ARCHIVED
    
    def test_delete_thread(self):
        """Test deleting a thread."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        
        deleted = thread.delete()
        
        assert deleted.status == ThreadStatus.DELETED
    
    def test_update_title(self):
        """Test updating thread title."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000", title="Old Title")
        
        updated = thread.update_title("New Title")
        
        assert updated.title == "New Title"
    
    def test_get_last_message(self):
        """Test getting last message from thread."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        message1 = Message.create_user_message(thread_id=thread.thread_id, content="First")
        message2 = Message.create_user_message(thread_id=thread.thread_id, content="Second")
        
        thread = thread.add_message(message1)
        thread = thread.add_message(message2)
        
        last_message = thread.get_last_message()
        assert last_message.content == "Second"
    
    def test_thread_to_dict(self):
        """Test thread to_dict conversion."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000", title="Test")
        
        result = thread.to_dict()
        
        assert result["user_id"] == thread.user_id
        assert result["title"] == "Test"
        assert result["status"] == "active"
        assert result["message_count"] == 0
        assert "thread_id" in result
        assert "created_at" in result
    
    def test_thread_to_dict_with_messages(self):
        """Test thread to_dict with messages included."""
        thread = Thread.create_new(user_id="123e4567-e89b-12d3-a456-426614174000")
        message = Message.create_user_message(thread_id=thread.thread_id, content="Test")
        thread = thread.add_message(message)
        
        result = thread.to_dict(include_messages=True)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Test"

