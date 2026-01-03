"""
Factory for creating LLM provider adapters.
Supports multiple LLM providers (OpenAI, Gemini, etc.) with a unified interface.
"""
import logging
import os
from enum import Enum
from typing import Optional

from src.domain.ports.ai_chat_service_port import AIChatServicePort

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    # Add more providers as needed
    # ANTHROPIC = "anthropic"
    # COHERE = "cohere"


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create_provider(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> AIChatServicePort:
        """
        Create an LLM provider instance based on configuration.
        
        Args:
            provider: Provider name (openai, gemini). If None, auto-detects from available API keys.
            api_key: Optional API key. If None, reads from environment variables.
            model: Optional model name. Uses provider defaults if not specified.
            
        Returns:
            AIChatServicePort: Configured LLM provider instance
            
        Raises:
            ValueError: If no provider can be created (no API keys available)
            RuntimeError: If provider is specified but not available
        """
        # Auto-detect provider if not specified
        if not provider:
            provider = LLMProviderFactory._auto_detect_provider()
        
        provider = provider.lower()
        
        # Create provider instance
        if provider == LLMProvider.OPENAI.value:
            return LLMProviderFactory._create_openai_provider(api_key, model)
        elif provider == LLMProvider.GEMINI.value:
            return LLMProviderFactory._create_gemini_provider(api_key, model)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {[p.value for p in LLMProvider]}"
            )
    
    @staticmethod
    def _auto_detect_provider() -> str:
        """
        Auto-detect provider based on available API keys.
        Priority: OpenAI > Gemini
        
        Returns:
            str: Provider name
            
        Raises:
            ValueError: If no API keys are available
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GOOGLE_API_KEY")
        
        if openai_key:
            logger.info("Auto-detected OpenAI provider (OPENAI_API_KEY found)")
            return LLMProvider.OPENAI.value
        elif gemini_key:
            logger.info("Auto-detected Gemini provider (GOOGLE_API_KEY found)")
            return LLMProvider.GEMINI.value
        else:
            raise ValueError(
                "No LLM provider API keys found. "
                "Please set OPENAI_API_KEY or GOOGLE_API_KEY environment variable, "
                "or specify LLM_PROVIDER environment variable."
            )
    
    @staticmethod
    def _create_openai_provider(
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> AIChatServicePort:
        """Create OpenAI provider instance."""
        from src.infra.services.ai.openai_chat_service import OpenAIChatService
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Please set OPENAI_API_KEY environment variable."
            )
        
        model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        return OpenAIChatService(api_key=api_key, model=model)
    
    @staticmethod
    def _create_gemini_provider(
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> AIChatServicePort:
        """Create Gemini provider instance."""
        from src.infra.services.ai.gemini_chat_service import GeminiChatService
        
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Google API key not found. "
                "Please set GOOGLE_API_KEY environment variable."
            )
        
        model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        return GeminiChatService(api_key=api_key, model=model)

