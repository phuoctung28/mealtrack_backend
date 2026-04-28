"""
Cache eviction and memory monitoring utilities for GeminiModelManager.
Handles LRU eviction, TTL expiry, and process memory checks.
"""
import gc
import logging
from typing import Dict, Optional, Any

from src.infra.services.ai.gemini_model_config import CachedModel

logger = logging.getLogger(__name__)


def evict_expired(models: Dict[str, CachedModel], ttl_seconds: int) -> int:
    """Evict all expired models. Returns count of evicted models."""
    expired_keys = [
        key for key, cached in models.items() if cached.is_expired(ttl_seconds)
    ]
    for key in expired_keys:
        del models[key]
        logger.debug(f"Evicted expired model: {key}")
    return len(expired_keys)


def evict_lru(models: Dict[str, CachedModel]) -> Optional[str]:
    """Evict the least recently used model. Returns evicted key or None."""
    if not models:
        return None
    lru_key = min(models.keys(), key=lambda k: models[k].last_accessed)
    del models[lru_key]
    logger.debug(f"Evicted LRU model: {lru_key}")
    return lru_key


def check_memory_and_evict(
    models: Dict[str, CachedModel],
    memory_warning_threshold_mb: int,
) -> None:
    """Check process memory and evict models if threshold exceeded."""
    try:
        import psutil

        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)

        if memory_mb > memory_warning_threshold_mb:
            logger.warning(
                f"High memory usage: {memory_mb:.1f}MB > {memory_warning_threshold_mb}MB. "
                f"Evicting LRU models..."
            )
            evict_count = max(1, len(models) // 2)
            for _ in range(evict_count):
                if models:
                    evict_lru(models)
            gc.collect()
            new_memory_mb = process.memory_info().rss / (1024 * 1024)
            logger.debug(f"After eviction: {new_memory_mb:.1f}MB")
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Memory check failed: {e}")


def clear_cache(models: Dict[str, CachedModel]) -> int:
    """Clear all cached model instances. Returns count cleared."""
    count = len(models)
    models.clear()
    logger.debug(f"Cleared {count} cached model instances")
    return count


def get_cache_stats(
    models: Dict[str, CachedModel],
    max_cache_size: int,
    ttl_seconds: int,
) -> Dict[str, Any]:
    """Return detailed cache statistics."""
    import time

    stats: Dict[str, Any] = {
        "cache_size": len(models),
        "max_cache_size": max_cache_size,
        "ttl_seconds": ttl_seconds,
        "models": {},
    }
    for key, cached in models.items():
        stats["models"][key] = {
            "age_seconds": time.time() - cached.created_at,
            "last_accessed_seconds_ago": time.time() - cached.last_accessed,
            "access_count": cached.access_count,
            "expired": cached.is_expired(ttl_seconds),
        }
    return stats


def get_memory_usage_mb() -> Optional[float]:
    """Get current process memory usage in MB, or None if psutil unavailable."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        return None
    except Exception:
        return None
