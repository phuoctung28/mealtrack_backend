"""Explicit provider+model router for AI inference."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.services.ai.model_route import ModelRoute

logger = logging.getLogger(__name__)


class AIInferenceRouter:
    """Routes AI requests through explicit provider+model chains."""

    def __init__(
        self,
        *,
        providers: dict[str, AIProviderPort],
        routes: dict[ModelPurpose, list[ModelRoute]],
    ) -> None:
        self._providers = providers
        self._routes = routes

    def get_routes(self, purpose: ModelPurpose) -> list[ModelRoute]:
        return list(self._routes.get(purpose, self._routes[ModelPurpose.GENERAL]))

    async def generate(
        self,
        *,
        purpose: ModelPurpose,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        routes = self.get_routes(purpose)
        attempted: list[str] = []
        last_error: str | None = None

        for route in routes:
            provider = self._providers.get(route.provider)
            if provider is None:
                continue
            if AICapability.TEXT_GENERATION not in provider.supported_capabilities:
                continue

            attempted.append(f"{route.provider}:{route.model}")
            try:
                return await provider.generate(
                    model=route.model,
                    prompt=prompt,
                    system_message=system_message,
                    response_type=response_type,
                    max_tokens=max_tokens,
                    schema=schema,
                    purpose_hint=purpose.value,
                    **kwargs,
                )
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient(provider.extract_error_code(exc)):
                    raise
                logger.warning(
                    "[AI-ROUTER-FALLBACK] purpose=%s provider=%s model=%s error=%s",
                    purpose.value,
                    route.provider,
                    route.model,
                    last_error[:160],
                )

        raise AIUnavailableError(
            f"All providers failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    async def generate_with_vision(
        self,
        *,
        purpose: ModelPurpose,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        routes = self.get_routes(purpose)
        attempted: list[str] = []
        last_error: str | None = None

        for route in routes:
            provider = self._providers.get(route.provider)
            if provider is None:
                continue
            if AICapability.VISION not in provider.supported_capabilities:
                continue

            attempted.append(f"{route.provider}:{route.model}")
            try:
                return await provider.generate_with_vision(
                    model=route.model,
                    prompt=prompt,
                    image_data=image_data,
                    system_message=system_message,
                    purpose_hint=purpose.value,
                    **kwargs,
                )
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient(provider.extract_error_code(exc)):
                    raise
                logger.warning(
                    "[AI-VISION-ROUTER-FALLBACK] purpose=%s provider=%s model=%s error=%s",
                    purpose.value,
                    route.provider,
                    route.model,
                    last_error[:160],
                )

        raise AIUnavailableError(
            f"All vision providers failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    def _is_transient(self, error_code: int | str | None) -> bool:
        return error_code in {429, 500, 502, 503, 504, "timeout", "connection"}
