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

    async def get_product(
        self, barcode: str, language: str = "en", product_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Search barcode nutrition via web search + AI extraction."""
        try:
            snippets = await self._search_barcode(barcode, product_name)
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

    async def _search_barcode(self, barcode: str, product_name: Optional[str] = None) -> Optional[str]:
        """Search Brave for barcode nutrition info, return combined snippets."""
        try:
            # Search with barcode + product name if available, otherwise just barcode
            query = f"{barcode} {product_name} nutrition" if product_name else f"{barcode} barcode product"
            client = self._get_client()
            response = await client.get(
                self.SEARCH_URL,
                params={"q": query, "count": 5},
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
                url = r.get("url", "")
                snippets.append(f"{title}: {description}")
                logger.debug(f"Brave result for {barcode}: {title} | {url}")

            combined = "\n\n".join(snippets)
            logger.debug(f"Brave snippets for {barcode} ({len(results)} results, {len(combined)} chars)")
            return combined
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
                "If snippets mention nutrition values per serving, convert to per 100g. "
                "If snippets identify the product but lack exact macros, estimate based on "
                "your knowledge of similar products and set confidence to medium. "
                "Return ONLY valid JSON with these fields: "
                '{"name": "product name", "brand": "brand or null", '
                '"protein_100g": float, "carbs_100g": float, "fat_100g": float, '
                '"fiber_100g": float, "sugar_100g": float, "serving_size": "description or null", '
                '"confidence": "high|medium|low"} '
                "Return null ONLY if you cannot identify the product at all from the snippets."
            )

            user_prompt = (
                f"Barcode: {barcode}\nLanguage: {language}\n\nWeb search snippets:\n{snippets}"
            )

            result = self._meal_gen.generate_meal_plan(
                user_prompt, system_prompt, response_type="json",
                max_tokens=500, model_purpose="barcode",
            )

            if not result or not isinstance(result, dict):
                return None

            # Accept all confidence levels — the data is from web search,
            # user will verify in editable UI. Only reject if macros are missing.
            confidence = result.get("confidence", "low")
            if confidence == "low":
                result["is_estimate"] = True  # Mark low-confidence as estimate
                logger.debug(f"Brave+AI extraction low confidence for {barcode}, marking as estimate")

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
