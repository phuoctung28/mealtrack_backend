from unittest.mock import MagicMock

import pytest

from src.domain.ports.cache_port import CachePort


def test_cache_port_is_abstract():
    from abc import ABC
    assert issubclass(CachePort, ABC)


def test_cache_port_cannot_be_instantiated():
    with pytest.raises(TypeError):
        CachePort()


def test_cache_service_implements_cache_port():
    from src.infra.cache.cache_service import CacheService

    # Verify that CacheService is a subclass of CachePort
    assert issubclass(CacheService, CachePort)

    # Verify that CacheService can be instantiated and is an instance of CachePort
    mock_redis = MagicMock()
    instance = CacheService(redis_client=mock_redis)
    assert isinstance(instance, CachePort)
