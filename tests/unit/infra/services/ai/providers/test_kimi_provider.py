import pytest
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.kimi_provider import KimiProvider


@pytest.fixture
def provider():
    return KimiProvider()


def test_provider_name(provider):
    assert provider.provider_name == "kimi"


def test_supported_capabilities(provider):
    caps = provider.supported_capabilities
    assert AICapability.TEXT_GENERATION in caps
    assert AICapability.VISION not in caps


def test_get_available_models(provider):
    models = provider.get_available_models()
    assert "moonshot-v1-8k" in models


@pytest.mark.asyncio
async def test_generate_raises_not_implemented(provider):
    with pytest.raises(NotImplementedError, match="Kimi provider not yet implemented"):
        await provider.generate(
            model="moonshot-v1-8k",
            prompt="test",
            system_message="test",
        )


@pytest.mark.asyncio
async def test_generate_with_vision_not_supported(provider):
    with pytest.raises(NotImplementedError, match="vision"):
        await provider.generate_with_vision(
            model="moonshot-v1-8k",
            prompt="test",
            image_data=b"fake",
        )
