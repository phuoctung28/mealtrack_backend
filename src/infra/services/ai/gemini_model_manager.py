"""
Singleton manager for ChatGoogleGenerativeAI model instances.
Reduces memory usage by reusing model instances across services.

Safeguards:
- Thread-safe with proper locking
- TTL-based cache eviction
- Max cache size limit with LRU eviction
- Memory monitoring
- Reset method for testing

Recommended deployment for low-memory environments (512MB):
- Use UVICORN_WORKERS=1 to avoid duplicate singletons
- Enable memory monitoring in production
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GeminiModelPurpose(str, Enum):
    """Purpose-based model selection for rate limit distribution.

    Each purpose maps to a different Gemini model to distribute
    API calls across multiple rate limit pools (5-10 RPM each).
    """

    GENERAL = "general"  # Default, backward compatible
    MEAL_NAMES = "meal_names"  # High RPM (10/min) for fast name generation
    RECIPE_PRIMARY = "recipe_primary"  # Recipe gen pool 1 (5 RPM)
    RECIPE_SECONDARY = "recipe_secondary"  # Recipe gen pool 2 (5 RPM)


# Default cache settings
DEFAULT_MAX_CACHE_SIZE = 5  # Max number of model instances
DEFAULT_TTL_SECONDS = 3600  # 1 hour TTL for cached models
MEMORY_WARNING_THRESHOLD_MB = 400  # Warn when process exceeds this


@dataclass
class CachedModel:
    """Wrapper for cached model with metadata."""

    model: Any  # ChatGoogleGenerativeAI
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this cached model has expired."""
        return (time.time() - self.created_at) > ttl_seconds


class GeminiModelManager:
    """
    Thread-safe singleton that manages a pool of ChatGoogleGenerativeAI instances.

    Reuses models when configuration matches (temperature, max_tokens, etc.)
    to minimize memory usage.

    Features:
    - Automatic TTL-based eviction
    - LRU eviction when max cache size exceeded
    - Memory monitoring with warnings
    - Thread-safe operations
    """

    _instance: Optional["GeminiModelManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the manager. Should only be called once via get_instance()."""
        if GeminiModelManager._instance is not None:
            raise RuntimeError(
                "GeminiModelManager is a singleton. Use get_instance() instead."
            )

        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._models: Dict[str, CachedModel] = {}
        self._model_lock = threading.Lock()

        # Cache configuration
        self.max_cache_size = int(
            os.getenv("GEMINI_MAX_CACHE_SIZE", DEFAULT_MAX_CACHE_SIZE)
        )
        self.ttl_seconds = int(os.getenv("GEMINI_CACHE_TTL", DEFAULT_TTL_SECONDS))
        self.memory_warning_threshold_mb = int(
            os.getenv("MEMORY_WARNING_THRESHOLD_MB", MEMORY_WARNING_THRESHOLD_MB)
        )

        logger.info(
            f"GeminiModelManager initialized: model={self.model_name}, "
            f"max_cache={self.max_cache_size}, ttl={self.ttl_seconds}s"
        )

    @classmethod
    def get_instance(cls) -> "GeminiModelManager":
        """
        Get the singleton instance of GeminiModelManager.

        Returns:
            GeminiModelManager: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    # Create instance without triggering __init__ check
                    instance = cls.__new__(cls)
                    # Manually initialize attributes
                    instance.api_key = os.getenv("GOOGLE_API_KEY")
                    if not instance.api_key:
                        raise ValueError("GOOGLE_API_KEY environment variable not set")

                    instance.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                    instance._models = {}
                    instance._model_lock = threading.Lock()

                    # Cache configuration
                    instance.max_cache_size = int(
                        os.getenv("GEMINI_MAX_CACHE_SIZE", DEFAULT_MAX_CACHE_SIZE)
                    )
                    instance.ttl_seconds = int(
                        os.getenv("GEMINI_CACHE_TTL", DEFAULT_TTL_SECONDS)
                    )
                    instance.memory_warning_threshold_mb = int(
                        os.getenv(
                            "MEMORY_WARNING_THRESHOLD_MB", MEMORY_WARNING_THRESHOLD_MB
                        )
                    )

                    logger.info(
                        f"GeminiModelManager initialized: model={instance.model_name}, "
                        f"max_cache={instance.max_cache_size}, ttl={instance.ttl_seconds}s"
                    )

                    cls._instance = instance
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance. Use for testing only.

        This clears all cached models and resets the singleton,
        allowing a fresh instance to be created on next get_instance() call.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.clear_cache()
                cls._instance = None
                logger.info("GeminiModelManager singleton reset")

    def _get_config_key(
        self,
        model_name: str = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate a cache key for model configuration.

        Args:
            model_name: Model name to include in cache key (for multi-model support)
            temperature: Model temperature
            max_output_tokens: Maximum output tokens
            response_mime_type: Response MIME type (e.g., "application/json")
            **kwargs: Additional configuration parameters

        Returns:
            str: Configuration cache key
        """
        # Include model name in key for multi-model differentiation
        model = model_name or self.model_name
        # Create a deterministic key from configuration
        key_parts = [
            f"model={model}",
            f"temp={temperature:.1f}",
            (
                f"max_tokens={max_output_tokens}"
                if max_output_tokens
                else "max_tokens=None"
            ),
            (
                f"mime_type={response_mime_type}"
                if response_mime_type
                else "mime_type=None"
            ),
        ]

        # Add any other significant config params
        for k, v in sorted(kwargs.items()):
            if k not in ["google_api_key", "model", "convert_system_message_to_human"]:
                key_parts.append(f"{k}={v}")

        return "|".join(key_parts)

    def get_model(
        self,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
        **kwargs,
    ):
        """
        Get a ChatGoogleGenerativeAI instance with the specified configuration.

        Reuses existing instances when configuration matches to save memory.
        Automatically evicts expired or LRU entries when needed.

        Args:
            temperature: Model temperature (default: 0.7)
            max_output_tokens: Maximum output tokens
            response_mime_type: Response MIME type (e.g., "application/json")
            **kwargs: Additional configuration parameters

        Returns:
            ChatGoogleGenerativeAI: Configured model instance
        """
        config_key = self._get_config_key(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            **kwargs,
        )

        with self._model_lock:
            # Check memory and evict if needed
            self._check_memory_and_evict()

            # Evict expired entries
            self._evict_expired()

            # Check if we have a cached model
            if config_key in self._models:
                cached = self._models[config_key]
                if not cached.is_expired(self.ttl_seconds):
                    cached.touch()
                    logger.debug(f"Reusing cached model: {config_key}")
                    return cached.model
                else:
                    # Expired, remove it
                    del self._models[config_key]
                    logger.debug(f"Evicted expired model: {config_key}")

            # Evict LRU if at max capacity
            if len(self._models) >= self.max_cache_size:
                self._evict_lru()

            # Create new model instance
            model = self._create_model(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type=response_mime_type,
                **kwargs,
            )

            self._models[config_key] = CachedModel(model=model)
            logger.info(
                f"Created new ChatGoogleGenerativeAI: {config_key} "
                f"(cache size: {len(self._models)}/{self.max_cache_size})"
            )

            return model

    def _create_model(
        self,
        temperature: float,
        max_output_tokens: Optional[int],
        response_mime_type: Optional[str],
        model_name: str = None,
        **kwargs,
    ):
        """Create a new ChatGoogleGenerativeAI instance.

        Args:
            temperature: Model temperature
            max_output_tokens: Maximum output tokens
            response_mime_type: Response MIME type
            model_name: Optional model name override (for multi-model support)
            **kwargs: Additional configuration parameters
        """
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Use provided model_name or fall back to default
        model = model_name or self.model_name

        model_config = {
            "model": model,
            "temperature": temperature,
            "google_api_key": self.api_key,
            "convert_system_message_to_human": True,
        }

        if max_output_tokens is not None:
            model_config["max_output_tokens"] = max_output_tokens

        if response_mime_type is not None:
            model_config["response_mime_type"] = response_mime_type

        # Add any additional kwargs
        for k, v in kwargs.items():
            if k not in ["google_api_key", "model"]:
                model_config[k] = v

        return ChatGoogleGenerativeAI(**model_config)

    def _get_model_name_for_purpose(self, purpose: GeminiModelPurpose) -> str:
        """Resolve model name for given purpose from env vars.

        Maps each purpose to a specific model with separate rate limit pool.
        Falls back to default model if env var not set.
        """
        purpose_to_env = {
            GeminiModelPurpose.GENERAL: "GEMINI_MODEL",
            GeminiModelPurpose.MEAL_NAMES: "GEMINI_MODEL_NAMES",
            GeminiModelPurpose.RECIPE_PRIMARY: "GEMINI_MODEL_RECIPE_PRIMARY",
            GeminiModelPurpose.RECIPE_SECONDARY: "GEMINI_MODEL_RECIPE_SECONDARY",
        }

        defaults = {
            GeminiModelPurpose.GENERAL: "gemini-2.5-flash",
            GeminiModelPurpose.MEAL_NAMES: "gemini-2.5-flash-lite",
            GeminiModelPurpose.RECIPE_PRIMARY: "gemini-2.5-flash",
            GeminiModelPurpose.RECIPE_SECONDARY: "gemini-3-flash",
        }

        env_var = purpose_to_env.get(purpose, "GEMINI_MODEL")
        return os.getenv(env_var, defaults.get(purpose, self.model_name))

    def get_model_for_purpose(
        self,
        purpose: GeminiModelPurpose = GeminiModelPurpose.GENERAL,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
        **kwargs,
    ):
        """Get model instance configured for specific purpose.

        Uses different model names based on purpose to distribute
        rate limit usage across multiple free-tier pools.

        Args:
            purpose: The intended use (MEAL_NAMES, RECIPE_PRIMARY, etc.)
            temperature: Model temperature (default: 0.7)
            max_output_tokens: Maximum output tokens
            response_mime_type: Response MIME type (e.g., "application/json")
            **kwargs: Additional configuration parameters

        Returns:
            ChatGoogleGenerativeAI: Configured model instance
        """
        model_name = self._get_model_name_for_purpose(purpose)

        config_key = self._get_config_key(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            **kwargs,
        )

        with self._model_lock:
            # Check memory and evict if needed
            self._check_memory_and_evict()

            # Evict expired entries
            self._evict_expired()

            # Check if we have a cached model
            if config_key in self._models:
                cached = self._models[config_key]
                if not cached.is_expired(self.ttl_seconds):
                    cached.touch()
                    logger.debug(
                        f"Reusing cached model for purpose={purpose.value}: {config_key}"
                    )
                    return cached.model
                else:
                    # Expired, remove it
                    del self._models[config_key]
                    logger.debug(f"Evicted expired model: {config_key}")

            # Evict LRU if at max capacity
            if len(self._models) >= self.max_cache_size:
                self._evict_lru()

            # Create new model instance with specific model name
            model = self._create_model(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type=response_mime_type,
                model_name=model_name,
                **kwargs,
            )

            self._models[config_key] = CachedModel(model=model)
            logger.info(
                f"Created ChatGoogleGenerativeAI for purpose={purpose.value}: "
                f"model={model_name} | {config_key} "
                f"(cache size: {len(self._models)}/{self.max_cache_size})"
            )

            return model

    def _evict_expired(self) -> int:
        """Evict all expired models. Returns count of evicted models."""
        expired_keys = [
            key
            for key, cached in self._models.items()
            if cached.is_expired(self.ttl_seconds)
        ]

        for key in expired_keys:
            del self._models[key]
            logger.debug(f"Evicted expired model: {key}")

        return len(expired_keys)

    def _evict_lru(self) -> Optional[str]:
        """Evict the least recently used model. Returns evicted key or None."""
        if not self._models:
            return None

        # Find LRU (oldest last_accessed)
        lru_key = min(self._models.keys(), key=lambda k: self._models[k].last_accessed)

        del self._models[lru_key]
        logger.info(f"Evicted LRU model: {lru_key}")
        return lru_key

    def _check_memory_and_evict(self) -> None:
        """Check process memory and evict models if threshold exceeded."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)

            if memory_mb > self.memory_warning_threshold_mb:
                logger.warning(
                    f"High memory usage: {memory_mb:.1f}MB > {self.memory_warning_threshold_mb}MB. "
                    f"Evicting LRU models..."
                )
                # Evict half of cached models
                evict_count = max(1, len(self._models) // 2)
                for _ in range(evict_count):
                    if self._models:
                        self._evict_lru()

                # Force garbage collection
                import gc

                gc.collect()

                new_memory_mb = process.memory_info().rss / (1024 * 1024)
                logger.info(f"After eviction: {new_memory_mb:.1f}MB")
        except ImportError:
            # psutil not available, skip memory check
            pass
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")

    def clear_cache(self) -> int:
        """
        Clear all cached model instances.

        Returns:
            int: Number of models cleared
        """
        with self._model_lock:
            count = len(self._models)
            self._models.clear()
            logger.info(f"Cleared {count} cached model instances")
            return count

    def get_cache_size(self) -> int:
        """Get the number of cached model instances."""
        with self._model_lock:
            return len(self._models)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics.

        Returns:
            Dict with cache stats including size, model configs, and access counts
        """
        with self._model_lock:
            stats = {
                "cache_size": len(self._models),
                "max_cache_size": self.max_cache_size,
                "ttl_seconds": self.ttl_seconds,
                "models": {},
            }

            for key, cached in self._models.items():
                stats["models"][key] = {
                    "age_seconds": time.time() - cached.created_at,
                    "last_accessed_seconds_ago": time.time() - cached.last_accessed,
                    "access_count": cached.access_count,
                    "expired": cached.is_expired(self.ttl_seconds),
                }

            return stats

    def get_memory_usage_mb(self) -> Optional[float]:
        """
        Get current process memory usage in MB.

        Returns:
            float: Memory usage in MB, or None if psutil not available
        """
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return None
        except Exception:
            return None
