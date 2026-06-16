"""AI infrastructure package — single entrypoint via GeminiService."""

from src.infra.ai.gemini_service import GeminiService
from src.infra.ai.model_config import FALLBACK_CHAINS, ModelPurpose

__all__ = ["GeminiService", "ModelPurpose", "FALLBACK_CHAINS"]
