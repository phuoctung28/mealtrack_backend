"""
OpenAI implementation of AI chat service.
"""
import logging
import os
from typing import List, Dict, Any, Optional, AsyncIterator

from src.domain.ports.ai_chat_service_port import AIChatServicePort

logger = logging.getLogger(__name__)


class OpenAIChatService(AIChatServicePort):
    """OpenAI implementation of AI chat service."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
                logger.info(f"OpenAI chat service initialized with model {self.model}")
            except ImportError:
                logger.warning("OpenAI package not installed. Install with: pip install openai")
        else:
            logger.warning("OPENAI_API_KEY not set. AI responses will not be available.")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate AI response using OpenAI API."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check API key.")
        
        # Validate temperature parameter
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        
        try:
            # Prepare messages
            formatted_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation messages
            formatted_messages.extend(messages)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Prepare metadata
            metadata = {
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
            return {
                "content": content,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise RuntimeError(f"Failed to generate AI response: {str(e)}")
    
    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate AI response with streaming chunks."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check API key.")
        
        # Validate temperature parameter
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        
        try:
            # Prepare messages
            formatted_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation messages
            formatted_messages.extend(messages)
            
            # Call OpenAI API with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Yield chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "chunk": chunk.choices[0].delta.content,
                        "metadata": {
                            "model": chunk.model,
                            "finish_reason": chunk.choices[0].finish_reason
                        }
                    }
        
        except Exception as e:
            logger.error(f"Error generating streaming OpenAI response: {e}")
            raise RuntimeError(f"Failed to generate streaming AI response: {str(e)}")

