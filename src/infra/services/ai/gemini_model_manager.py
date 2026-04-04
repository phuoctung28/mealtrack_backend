"""
Singleton manager for ChatGoogleGenerativeAI model instances.
Thread-safe, TTL+LRU cache eviction, memory monitoring.
Config constants: gemini_model_config.py | Cache logic: gemini_cache_handler.py
"""

import logging
import os
import threading
from typing import Optional, Dict, Any

from src.infra.services.ai.gemini_model_config import (
    CachedModel,
    GeminiModelPurpose,
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_TTL_SECONDS,
    MEMORY_WARNING_THRESHOLD_MB,
    PURPOSE_MODEL_DEFAULTS,
    PURPOSE_ENV_VARS,
)
import src.infra.services.ai.gemini_cache_handler as cache_handler

logger = logging.getLogger(__name__)


class GeminiModelManager:
    """Thread-safe singleton managing a pool of ChatGoogleGenerativeAI instances."""

    _instance: Optional["GeminiModelManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GeminiModelManager":
        """Get the singleton instance of GeminiModelManager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls.__new__(cls)
                    instance._init_state()
                    cls._instance = instance
        return cls._instance

    def _init_state(self) -> None:
        """Initialize instance state (called once via get_instance)."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._models: Dict[str, CachedModel] = {}
        self._model_lock = threading.Lock()

        self.max_cache_size = int(os.getenv("GEMINI_MAX_CACHE_SIZE", DEFAULT_MAX_CACHE_SIZE))
        self.ttl_seconds = int(os.getenv("GEMINI_CACHE_TTL", DEFAULT_TTL_SECONDS))
        self.memory_warning_threshold_mb = int(
            os.getenv("MEMORY_WARNING_THRESHOLD_MB", MEMORY_WARNING_THRESHOLD_MB)
        )
        logger.info(
            f"GeminiModelManager initialized: model={self.model_name}, "
            f"max_cache={self.max_cache_size}, ttl={self.ttl_seconds}s"
        )

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Use for testing only."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.clear_cache()
                cls._instance = None
                logger.info("GeminiModelManager singleton reset")

    def _get_config_key(self, model_name: str = None, temperature: float = 0.7,
                        max_output_tokens: Optional[int] = None,
                        response_mime_type: Optional[str] = None, **kwargs) -> str:
        """Generate a deterministic cache key from model configuration."""
        model = model_name or self.model_name
        key_parts = [
            f"model={model}", f"temp={temperature:.1f}",
            f"max_tokens={max_output_tokens}" if max_output_tokens else "max_tokens=None",
            f"mime_type={response_mime_type}" if response_mime_type else "mime_type=None",
        ]
        skip = {"google_api_key", "model", "convert_system_message_to_human"}
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if k not in skip)
        return "|".join(key_parts)

    def _create_model(self, temperature: float, max_output_tokens: Optional[int],
                      response_mime_type: Optional[str], model_name: str = None, **kwargs):
        """Create a new ChatGoogleGenerativeAI instance."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        cfg = {"model": model_name or self.model_name, "temperature": temperature,
               "google_api_key": self.api_key, "convert_system_message_to_human": True}
        if max_output_tokens is not None:
            cfg["max_output_tokens"] = max_output_tokens
        if response_mime_type is not None:
            cfg["response_mime_type"] = response_mime_type
        cfg.update({k: v for k, v in kwargs.items() if k not in ("google_api_key", "model")})
        return ChatGoogleGenerativeAI(**cfg)

    def _get_or_create_model(self, config_key: str, model_name: str, temperature: float,
                              max_output_tokens: Optional[int], response_mime_type: Optional[str],
                              **kwargs):
        """Cache lookup then create. Caller must hold _model_lock."""
        cache_handler.check_memory_and_evict(self._models, self.memory_warning_threshold_mb)
        cache_handler.evict_expired(self._models, self.ttl_seconds)
        if config_key in self._models:
            cached = self._models[config_key]
            if not cached.is_expired(self.ttl_seconds):
                cached.touch()
                logger.debug(f"Reusing cached model: {config_key}")
                return cached.model
            del self._models[config_key]
        if len(self._models) >= self.max_cache_size:
            cache_handler.evict_lru(self._models)
        model = self._create_model(temperature, max_output_tokens, response_mime_type, model_name, **kwargs)
        self._models[config_key] = CachedModel(model=model)
        logger.info(f"Created ChatGoogleGenerativeAI: {config_key} ({len(self._models)}/{self.max_cache_size})")
        return model

    def get_model(self, temperature: float = 0.7, max_output_tokens: Optional[int] = None,
                  response_mime_type: Optional[str] = None, **kwargs):
        """Get a model instance with the specified configuration."""
        config_key = self._get_config_key(temperature=temperature, max_output_tokens=max_output_tokens,
                                           response_mime_type=response_mime_type, **kwargs)
        with self._model_lock:
            return self._get_or_create_model(
                config_key, self.model_name, temperature, max_output_tokens, response_mime_type, **kwargs
            )

    def get_model_for_purpose(
        self,
        purpose: GeminiModelPurpose = GeminiModelPurpose.GENERAL,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
        **kwargs,
    ):
        """Get model instance configured for specific purpose."""
        env_var = PURPOSE_ENV_VARS.get(purpose, "GEMINI_MODEL")
        model_name = os.getenv(env_var, PURPOSE_MODEL_DEFAULTS.get(purpose, self.model_name))

        if purpose in (GeminiModelPurpose.RECIPE_PRIMARY, GeminiModelPurpose.RECIPE_SECONDARY, GeminiModelPurpose.BARCODE):
            kwargs.setdefault("thinking_budget", 0)

        config_key = self._get_config_key(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            **kwargs,
        )
        with self._model_lock:
            return self._get_or_create_model(
                config_key, model_name, temperature, max_output_tokens, response_mime_type, **kwargs
            )

    def clear_cache(self) -> int:
        """Clear all cached model instances. Returns count cleared."""
        with self._model_lock:
            return cache_handler.clear_cache(self._models)

    def get_cache_size(self) -> int:
        """Get the number of cached model instances."""
        with self._model_lock:
            return len(self._models)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        with self._model_lock:
            return cache_handler.get_cache_stats(self._models, self.max_cache_size, self.ttl_seconds)

    def get_memory_usage_mb(self) -> Optional[float]:
        """Get current process memory usage in MB."""
        return cache_handler.get_memory_usage_mb()
