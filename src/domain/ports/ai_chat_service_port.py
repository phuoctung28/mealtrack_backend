"""
Port (interface) for AI chat service.
Defines the contract for AI chat implementations (OpenAI, Claude, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator


class AIChatServicePort(ABC):
    """Port for AI chat completion services."""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response based on conversation history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to set context
            temperature: Randomness of response (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with 'content' (response text) and 'metadata' (model info, tokens, etc.)
        """
        pass
    
    @abstractmethod
    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate AI response with streaming chunks.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to set context
            temperature: Randomness of response (0-1)
            max_tokens: Maximum tokens in response
            
        Yields:
            Dict with 'chunk' (text chunk) and optional 'metadata'
        """
        pass

