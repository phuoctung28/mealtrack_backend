"""
Unit tests for ChatResponseBuilder.
"""
import pytest
from datetime import datetime

from src.api.builders.chat_response_builder import ChatResponseBuilder
from src.api.schemas.response.chat_responses import MessageResponse, FollowUpQuestion, StructuredData


class TestChatResponseBuilder:
    """Test ChatResponseBuilder methods."""

    def test_build_message_response_with_follow_ups(self):
        """Test building message response with follow-up questions."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "follow_ups": [
                    {"id": "f1", "text": "Question 1", "type": "question"},
                    {"id": "f2", "text": "Question 2", "type": "suggestion", "metadata": {"key": "value"}}
                ]
            }
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert isinstance(result, MessageResponse)
        assert result.message_id == "msg-123"
        assert result.thread_id == "thread-456"
        assert result.role == "assistant"
        assert result.content == "Test message"
        assert result.follow_ups is not None
        assert len(result.follow_ups) == 2
        assert result.follow_ups[0].id == "f1"
        assert result.follow_ups[0].text == "Question 1"
        assert result.follow_ups[1].metadata == {"key": "value"}

    def test_build_message_response_with_structured_data_meals(self):
        """Test building message response with structured data (meals)."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "structured_data": {
                    "meals": [{"id": "meal-1", "name": "Chicken"}],
                    "recipes": []
                }
            }
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert result.structured_data is not None
        assert result.structured_data.meals is not None
        assert len(result.structured_data.meals) == 1
        assert result.structured_data.meals[0].name == "Chicken"
        assert result.structured_data.recipes == []

    def test_build_message_response_with_structured_data_recipes(self):
        """Test building message response with structured data (recipes)."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "structured_data": {
                    "meals": [],
                    "recipes": [{"id": "recipe-1", "name": "Pasta"}]
                }
            }
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert result.structured_data is not None
        assert result.structured_data.recipes == [{"id": "recipe-1", "name": "Pasta"}]

    def test_build_message_response_without_structured_data(self):
        """Test building message response without structured data."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert result.structured_data is None

    def test_build_message_response_with_empty_structured_data(self):
        """Test building message response with empty structured data."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "structured_data": {}
            }
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert result.structured_data is None

    def test_build_message_response_follow_ups_with_defaults(self):
        """Test building message response with follow-ups that have default values."""
        msg_dict = {
            "message_id": "msg-123",
            "thread_id": "thread-456",
            "role": "assistant",
            "content": "Test message",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "follow_ups": [
                    {"text": "Question without id"},
                    {}  # Empty follow-up
                ]
            }
        }
        
        result = ChatResponseBuilder.build_message_response(msg_dict)
        
        assert result.follow_ups is not None
        assert len(result.follow_ups) == 2
        assert result.follow_ups[0].id == "followup_0"
        assert result.follow_ups[0].type == "question"
        assert result.follow_ups[1].id == "followup_1"
        assert result.follow_ups[1].text == ""

    def test_build_message_list(self):
        """Test building a list of message responses."""
        messages = [
            {
                "message_id": "msg-1",
                "thread_id": "thread-1",
                "role": "user",
                "content": "Message 1",
                "created_at": datetime.now().isoformat(),
                "metadata": {}
            },
            {
                "message_id": "msg-2",
                "thread_id": "thread-1",
                "role": "assistant",
                "content": "Message 2",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "follow_ups": [{"text": "Follow up"}]
                }
            }
        ]
        
        result = ChatResponseBuilder.build_message_list(messages)
        
        assert len(result) == 2
        assert all(isinstance(msg, MessageResponse) for msg in result)
        assert result[0].message_id == "msg-1"
        assert result[1].message_id == "msg-2"
        assert result[1].follow_ups is not None

    def test_build_thread_with_messages_provided(self):
        """Test building thread with messages provided separately."""
        thread_data = {
            "thread_id": "thread-123",
            "title": "Test Thread",
            "created_at": datetime.now().isoformat()
        }
        messages = [
            {
                "message_id": "msg-1",
                "thread_id": "thread-123",
                "role": "user",
                "content": "Test",
                "created_at": datetime.now().isoformat(),
                "metadata": {}
            }
        ]
        
        result = ChatResponseBuilder.build_thread_with_messages(thread_data, messages)
        
        assert result["thread_id"] == "thread-123"
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], MessageResponse)

    def test_build_thread_with_messages_in_data(self):
        """Test building thread with messages already in thread_data."""
        thread_data = {
            "thread_id": "thread-123",
            "title": "Test Thread",
            "created_at": datetime.now().isoformat(),
            "messages": [
                {
                    "message_id": "msg-1",
                    "thread_id": "thread-123",
                    "role": "user",
                    "content": "Test",
                    "created_at": datetime.now().isoformat(),
                    "metadata": {}
                }
            ]
        }
        
        result = ChatResponseBuilder.build_thread_with_messages(thread_data)
        
        assert result["thread_id"] == "thread-123"
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], MessageResponse)

    def test_build_thread_without_messages(self):
        """Test building thread without messages."""
        thread_data = {
            "thread_id": "thread-123",
            "title": "Test Thread",
            "created_at": datetime.now().isoformat()
        }
        
        result = ChatResponseBuilder.build_thread_with_messages(thread_data)
        
        assert result["thread_id"] == "thread-123"
        assert "messages" not in result or result.get("messages") is None

