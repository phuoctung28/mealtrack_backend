import pytest
from abc import ABC
from src.domain.ports.ai_provider_port import AIProviderPort, AICapability


def test_ai_provider_port_is_abstract():
    assert issubclass(AIProviderPort, ABC)
    with pytest.raises(TypeError):
        AIProviderPort()


def test_ai_capability_enum_values():
    assert AICapability.TEXT_GENERATION.value == "text_generation"
    assert AICapability.VISION.value == "vision"
    assert AICapability.STRUCTURED_OUTPUT.value == "structured_output"


class ConcreteProvider(AIProviderPort):
    """Test implementation."""

    @property
    def provider_name(self) -> str:
        return "test"

    @property
    def supported_capabilities(self) -> set:
        return {AICapability.TEXT_GENERATION}

    def get_available_models(self) -> list:
        return ["test-model"]

    async def generate(self, model, prompt, system_message, **kwargs):
        return {"result": "test"}

    async def generate_with_vision(self, model, prompt, image_data, **kwargs):
        raise NotImplementedError("Vision not supported")


def test_concrete_provider_implements_interface():
    provider = ConcreteProvider()
    assert provider.provider_name == "test"
    assert AICapability.TEXT_GENERATION in provider.supported_capabilities
    assert provider.get_available_models() == ["test-model"]


@pytest.mark.asyncio
async def test_concrete_provider_generate():
    provider = ConcreteProvider()
    result = await provider.generate("test-model", "prompt", "system")
    assert result == {"result": "test"}
