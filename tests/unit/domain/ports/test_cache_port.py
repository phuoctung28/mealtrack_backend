from abc import ABC
from src.domain.ports.cache_port import CachePort


def test_cache_port_is_abstract():
    assert issubclass(CachePort, ABC)


def test_cache_port_cannot_be_instantiated():
    import pytest
    with pytest.raises(TypeError):
        CachePort()


def test_cache_service_implements_cache_port():
    from src.infra.cache.cache_service import CacheService
    assert issubclass(CacheService, CachePort)
