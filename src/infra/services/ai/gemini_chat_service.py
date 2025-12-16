"""
Google Gemini implementation of AI chat service.
Refactored to use AIResponseParser and SystemPrompts.
"""
import logging
import os
from typing import List, Dict, Any, Optional, AsyncIterator

from src.domain.ports.ai_chat_service_port import AIChatServicePort
from src.infra.services.ai.prompts import SystemPrompts

logger = logging.getLogger(__name__)


class GeminiChatService(AIChatServicePort):
    """Google Gemini implementation of AI chat service for meal planning."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.system_prompt = system_prompt or SystemPrompts.get_meal_planning_prompt()
        self.client = None

        if self.api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.client = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=0.7,
                    google_api_key=self.api_key,
                    convert_system_message_to_human=True
                )
                logger.info(f"Gemini chat service initialized with model {self.model_name}")
            except ImportError:
                logger.warning("langchain-google-genai package not installed. Install with: pip install langchain-google-genai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                logger.info(f"Tip: Using same model as food scanning: {self.model_name}")
        else:
            logger.warning("GOOGLE_API_KEY not set. AI responses will not be available.")

    def _get_client_for_temperature(self, temperature: float):
        """Get a client configured for the specified temperature."""
        if temperature == 0.7:
            return self.client

        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=temperature,
            google_api_key=self.api_key,
            convert_system_message_to_human=True
        )

    def _format_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str]
    ) -> List:
        """
        Format messages for Gemini API.

        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to prepend

        Returns:
            List of formatted message objects
        """
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        formatted_messages = []

        # Add system prompt
        effective_prompt = system_prompt if system_prompt is not None else self.system_prompt
        if effective_prompt:
            formatted_messages.append(SystemMessage(content=effective_prompt))

        # Add conversation messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted_messages.append(SystemMessage(content=content))
            elif role == "user":
                formatted_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_messages.append(AIMessage(content=content))

        return formatted_messages

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate AI response using Google Gemini API."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized. Check API key.")

        # Validate temperature parameter
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        try:
            # Format messages
            formatted_messages = self._format_messages(messages, system_prompt)

            # Get client for temperature
            client = self._get_client_for_temperature(temperature)

            # Call Gemini API
            response = await client.ainvoke(formatted_messages)

            # Extract response content
            content = response.content if hasattr(response, 'content') else str(response)

            # Prepare metadata (Gemini doesn't provide token usage in same way as OpenAI)
            metadata = {
                "model": self.model_name,
                "usage": {
                    "prompt_tokens": 0,  # Gemini doesn't expose this easily
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "finish_reason": "stop"
            }

            return {
                "content": content,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            raise RuntimeError(f"Failed to generate AI response: {str(e)}")

    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate AI response with streaming chunks using Gemini API."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized. Check API key.")

        # Validate temperature parameter
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        try:
            # Format messages
            formatted_messages = self._format_messages(messages, system_prompt)

            # Get client for temperature
            client = self._get_client_for_temperature(temperature)

            # Call Gemini API with streaming
            async for chunk in client.astream(formatted_messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    yield {
                        "chunk": content,
                        "metadata": {
                            "model": self.model_name,
                            "finish_reason": None
                        }
                    }

            # Final chunk with finish reason
            yield {
                "chunk": "",
                "metadata": {
                    "model": self.model_name,
                    "finish_reason": "stop"
                }
            }

        except Exception as e:
            logger.error(f"Error generating streaming Gemini response: {e}")
            raise RuntimeError(f"Failed to generate streaming AI response: {str(e)}")
