"""
Gemini / Imagen image generation adapter.

Uses the Imagen 3 REST endpoint to generate a food photograph, then
uploads the result to Cloudinary and returns the secure URL.

REST endpoint:
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}

Model default: imagen-3.0-fast-generate-001
Requires: GOOGLE_API_KEY, CLOUDINARY_* env vars.
"""
import base64
import logging
from typing import Optional

import httpx

from src.domain.ports.meal_image_retrieval_port import MealImageRetrievalPort

logger = logging.getLogger(__name__)

_IMAGEN_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"
_DEFAULT_MODEL = "imagen-3.0-fast-generate-001"


class GeminiImageGenerationAdapter(MealImageRetrievalPort):
    """Generate a meal image via Imagen 3, upload to Cloudinary, return URL."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model

    async def fetch_image(self, meal_name: str) -> Optional[str]:
        """Generate and upload a food image for the given meal name."""
        image_bytes = await self._generate_image(meal_name)
        if not image_bytes:
            return None
        return self._upload_to_cloudinary(image_bytes)

    async def _generate_image(self, meal_name: str) -> Optional[bytes]:
        prompt = (
            f"Professional food photography of {meal_name}, "
            "top-down view, natural lighting, restaurant quality, "
            "on a clean white plate, vibrant colors"
        )
        url = _IMAGEN_BASE.format(model=self._model)
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "1:1"},
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            predictions = data.get("predictions", [])
            if not predictions:
                logger.debug("Gemini image generation returned no predictions for '%s'.", meal_name)
                return None

            b64 = predictions[0].get("bytesBase64Encoded")
            if not b64:
                logger.debug("Gemini prediction missing bytesBase64Encoded for '%s'.", meal_name)
                return None

            return base64.b64decode(b64)

        except Exception as exc:
            logger.warning("Gemini image generation failed for '%s': %s", meal_name, exc)
            return None

    @staticmethod
    def _upload_to_cloudinary(image_bytes: bytes) -> Optional[str]:
        try:
            from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
            store = CloudinaryImageStore()
            url = store.save(image_bytes, "image/jpeg")
            logger.debug("Gemini image uploaded to Cloudinary: %s", url[:80] if url else "None")
            return url
        except Exception as exc:
            logger.warning("Cloudinary upload failed for Gemini-generated image: %s", exc)
            return None


def get_gemini_image_generation_adapter() -> Optional[GeminiImageGenerationAdapter]:
    """Return adapter if GOOGLE_API_KEY is configured, else None."""
    from src.infra.config.settings import settings
    if not settings.GOOGLE_API_KEY:
        return None
    model = settings.GEMINI_IMAGE_MODEL or _DEFAULT_MODEL
    return GeminiImageGenerationAdapter(api_key=settings.GOOGLE_API_KEY, model=model)
