"""
BraveSearchNutritionService - Search barcode nutrition via Brave Search + Gemini extraction.
"""
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class BraveSearchNutritionService:
    """Search for barcode nutrition info via Brave Search, extract macros via Gemini."""

    SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, meal_generation_service: Any, macro_validation_service: Any):
        self._api_key = api_key
        self._meal_gen = meal_generation_service
        self._macro_validator = macro_validation_service
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def get_product(self, barcode: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """Search barcode nutrition via web search + AI extraction."""
        try:
            snippets = await self._search_barcode(barcode)
            if not snippets:
                return None

            extracted = await self._extract_nutrition(barcode, snippets, language)
            if not extracted:
                return None

            validated = self._macro_validator.validate_and_correct(extracted)
            validated["barcode"] = barcode
            return validated
        except Exception as e:
            logger.warning(f"Brave search failed for barcode {barcode}: {e}")
            return None

    async def _search_barcode(self, barcode: str) -> Optional[str]:
        """Search Brave for barcode nutrition info, return combined snippets."""
        try:
            client = self._get_client()
            response = await client.get(
                self.SEARCH_URL,
                params={"q": f"{barcode} nutrition facts", "count": 5},
                headers={
                    "X-Subscription-Token": self._api_key,
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("web", {}).get("results", [])
            if not results:
                return None

            snippets = []
            for r in results[:5]:
                title = r.get("title", "")
                description = r.get("description", "")
                snippets.append(f"{title}: {description}")

            return "\n\n".join(snippets)
        except Exception as e:
            logger.warning(f"Brave search API error for {barcode}: {e}")
            return None

    async def _extract_nutrition(
        self, barcode: str, snippets: str, language: str
    ) -> Optional[Dict[str, Any]]:
        """Use Gemini to extract structured nutrition from search snippets."""
        try:
            system_prompt = (
                "You are a nutrition data extraction expert. "
                "Extract nutrition information per 100g from web search snippets about a food product. "
                "Return ONLY valid JSON with these fields: "
                '{"name": "product name", "brand": "brand or null", '
                '"protein_100g": float, "carbs_100g": float, "fat_100g": float, '
                '"fiber_100g": float, "sugar_100g": float, "serving_size": "description or null", '
                '"confidence": "high|medium|low"} '
                "If snippets don't contain enough nutrition data, return null. "
                "Be precise — only extract values explicitly stated in the snippets."
            )

            user_prompt = (
                f"Barcode: {barcode}\nLanguage: {language}\n\nWeb search snippets:\n{snippets}"
            )

            result = self._meal_gen.generate_meal_plan(
                user_prompt, system_prompt, response_type="json"
            )

            if not result or not isinstance(result, dict):
                return None

            confidence = result.get("confidence", "low")
            if confidence == "low":
                logger.info(f"Brave+AI extraction low confidence for {barcode}, skipping")
                return None

            required = ["protein_100g", "carbs_100g", "fat_100g"]
            if not all(result.get(f) is not None for f in required):
                return None

            return result
        except Exception as e:
            logger.warning(f"Gemini extraction failed for barcode {barcode}: {e}")
            return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


def get_brave_search_nutrition_service(
    meal_generation_service: Any = None,
    macro_validation_service: Any = None,
) -> Optional[BraveSearchNutritionService]:
    """Return a BraveSearchNutritionService if API key is configured, else None."""
    from src.infra.config.settings import settings

    if not settings.BRAVE_SEARCH_API_KEY:
        return None
    if not meal_generation_service or not macro_validation_service:
        return None
    return BraveSearchNutritionService(
        settings.BRAVE_SEARCH_API_KEY, meal_generation_service, macro_validation_service
    )
