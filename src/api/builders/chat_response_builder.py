"""
Chat response builder for constructing API responses.
Extracts response building logic from route handlers.
"""
from typing import Dict, List, Optional

from src.api.schemas.response.chat_responses import (
    MessageResponse,
    FollowUpQuestion,
    StructuredData
)


class ChatResponseBuilder:
    """Builds properly structured chat API responses."""

    @staticmethod
    def build_message_response(msg_dict: dict) -> MessageResponse:
        """
        Build MessageResponse with proper follow_ups and structured_data.

        Args:
            msg_dict: Dictionary containing message data with metadata

        Returns:
            MessageResponse with properly structured follow-ups and data
        """
        metadata = msg_dict.get("metadata") or {}
        follow_ups_raw = metadata.get("follow_ups", [])
        structured_data_raw = metadata.get("structured_data")

        # Convert raw follow_ups to FollowUpQuestion objects
        follow_ups = None
        if follow_ups_raw:
            follow_ups = [
                FollowUpQuestion(
                    id=f.get("id", f"followup_{i}"),
                    text=f.get("text", ""),
                    type=f.get("type", "question"),
                    metadata=f.get("metadata")
                )
                for i, f in enumerate(follow_ups_raw)
            ]

        # Convert raw structured_data to StructuredData
        structured_data = None
        if structured_data_raw and (
            structured_data_raw.get("meals") or structured_data_raw.get("recipes")
        ):
            structured_data = StructuredData(
                meals=structured_data_raw.get("meals"),
                recipes=structured_data_raw.get("recipes")
            )

        return MessageResponse(
            message_id=msg_dict.get("message_id"),
            thread_id=msg_dict.get("thread_id"),
            role=msg_dict.get("role"),
            content=msg_dict.get("content"),
            created_at=msg_dict.get("created_at"),
            metadata=metadata,
            follow_ups=follow_ups,
            structured_data=structured_data
        )

    @staticmethod
    def build_message_list(messages: List[dict]) -> List[MessageResponse]:
        """
        Build a list of MessageResponse objects from message dictionaries.

        Args:
            messages: List of message dictionaries

        Returns:
            List of MessageResponse objects
        """
        return [
            ChatResponseBuilder.build_message_response(msg)
            for msg in messages
        ]

    @staticmethod
    def build_thread_with_messages(
        thread_data: dict,
        messages: Optional[List[dict]] = None
    ) -> dict:
        """
        Build thread response with properly formatted messages.

        Args:
            thread_data: Thread dictionary data
            messages: Optional list of message dictionaries

        Returns:
            Thread data with formatted messages
        """
        result = thread_data.copy()

        # Convert messages if provided
        if messages:
            result["messages"] = ChatResponseBuilder.build_message_list(messages)
        elif "messages" in result and isinstance(result["messages"], list):
            # Convert existing messages in thread_data
            result["messages"] = ChatResponseBuilder.build_message_list(
                result["messages"]
            )

        return result
