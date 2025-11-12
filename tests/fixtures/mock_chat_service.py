"""
Mock implementation of AI chat service for testing.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator

from src.domain.ports.ai_chat_service_port import AIChatServicePort

logger = logging.getLogger(__name__)


class MockChatService(AIChatServicePort):
    """Mock AI chat service for testing."""
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate mock AI response."""
        # Simple echo response for testing
        last_message = messages[-1] if messages else {"content": ""}
        
        return {
            "content": f"This is a mock AI response to: {last_message.get('content', '')}",
            "metadata": {
                "model": "mock-model",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                },
                "finish_reason": "stop"
            }
        }
    
    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate mock streaming AI response."""
        # Simulate streaming by splitting response into chunks
        last_message = messages[-1] if messages else {"content": ""}
        response = f"This is a mock AI response to: {last_message.get('content', '')}"
        
        # Split into words and stream them
        words = response.split()
        for word in words:
            await asyncio.sleep(0.05)  # Simulate network delay
            yield {
                "chunk": word + " ",
                "metadata": {
                    "model": "mock-model",
                    "finish_reason": None
                }
            }
        
        # Final chunk with finish reason
        yield {
            "chunk": "",
            "metadata": {
                "model": "mock-model",
                "finish_reason": "stop"
            }
        }

