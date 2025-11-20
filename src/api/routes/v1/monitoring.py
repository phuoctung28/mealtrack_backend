"""
Monitoring endpoints for cache metrics.
"""
from fastapi import APIRouter, Depends

from src.api.base_dependencies import get_cache_monitor
from src.infra.cache.metrics import CacheMonitor

router = APIRouter(prefix="/v1/monitoring", tags=["Monitoring"])


@router.get("/cache/metrics")
async def cache_metrics(cache_monitor: CacheMonitor = Depends(get_cache_monitor)):
    """Return cache hit/miss statistics."""
    return cache_monitor.snapshot()

