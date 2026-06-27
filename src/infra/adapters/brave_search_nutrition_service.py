"""BraveSearchNutritionService - Search barcode nutrition via Brave Search + AI extraction."""

import logging
from typing import Any

import httpx

from src.domain.services.barcode.barcode_logging import redact_barcode
from src.domain.services.barcode.barcode_nutrition_validator import (
    validate_barcode_nutrition,
)
from src.domain.services.prompts.system_prompts import SystemPrompts
from src.infra.adapters.ai_json_utils import extract_json

logger = logging.getLogger(__name__)


class BraveSearchNutritionService:
    """Search for barcode nutrition info via Brave Search, extract macros via AI."""

    SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self, api_key: str, meal_generation_service: Any, macro_validation_service: Any
    ):
        self._api_key = api_key
        self._meal_gen = meal_generation_service
        self._macro_validator = macro_validation_service
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def get_product(
        self,
        barcode: str,
        language: str = "en",
        product_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Search barcode nutrition via web search + AI extraction."""
        try:
            snippets = await self._search_barcode(barcode, product_name)
            if not snippets:
                return None

            extracted = await self._extract_nutrition(barcode, snippets, language)
            if not extracted:
                return None

            validated = validate_barcode_nutrition(extracted)
            validated["barcode"] = barcode
            return validated
        except Exception as e:
            logger.warning(
                "Brave search failed for barcode_ref=%s error=%s",
                redact_barcode(barcode),
                type(e).__name__,
            )
            return None

    async def _search_barcode(
        self, barcode: str, product_name: str | None = None
    ) -> str | None:
        """Search Brave for barcode nutrition info, return combined snippets."""
        try:
            # Search with barcode + product name if available, otherwise just barcode
            query = (
                f"{barcode} {product_name} nutrition"
                if product_name
                else f"{barcode} barcode product"
            )
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
                snippets.append(f"{title}: {description}")
                logger.debug(
                    "Brave result for barcode_ref=%s title_present=%s url_present=%s",
                    redact_barcode(barcode),
                    bool(title),
                    bool(r.get("url")),
                )

            combined = "\n\n".join(snippets)
            logger.debug(
                "Brave snippets for barcode_ref=%s results=%d chars=%d",
                redact_barcode(barcode),
                len(results),
                len(combined),
            )
            return combined
        except Exception as e:
            logger.warning(
                "Brave search API error for barcode_ref=%s error=%s",
                redact_barcode(barcode),
                type(e).__name__,
            )
            return None

    async def _extract_nutrition(
        self, barcode: str, snippets: str, language: str
    ) -> dict[str, Any] | None:
        """Use AI to extract structured nutrition from search snippets."""
        try:
            system_prompt = SystemPrompts.BARCODE_BRAVE_EXTRACT
            user_prompt = f"Barcode: {barcode}\nLanguage: {language}\n\nWeb search snippets:\n{snippets}"

            result = await self._meal_gen.generate_meal_plan_async(
                user_prompt,
                system_prompt,
                response_type="text",
                max_tokens=500,
                model_purpose="barcode",
            )
            result = self._parse_extraction_result(result, barcode)

            if not result or not isinstance(result, dict):
                return None

            # Accept all confidence levels — the data is from web search,
            # user will verify in editable UI. Only reject if macros are missing.
            confidence = result.get("confidence", "low")
            if confidence == "low":
                result["is_estimate"] = True  # Mark low-confidence as estimate
                logger.debug(
                    "Brave+AI extraction low confidence for barcode_ref=%s",
                    redact_barcode(barcode),
                )

            required = ["protein_100g", "carbs_100g", "fat_100g"]
            if not all(result.get(f) is not None for f in required):
                return None

            return validate_barcode_nutrition(result)
        except Exception as e:
            logger.warning(
                "AI extraction failed for barcode_ref=%s error=%s",
                redact_barcode(barcode),
                type(e).__name__,
            )
            return None

    @staticmethod
    def _parse_extraction_result(result: Any, barcode: str) -> dict[str, Any] | None:
        """Parse Brave extraction output, treating uncertain prose as a miss."""
        if isinstance(result, dict) and "raw_content" not in result:
            return result

        raw = result.get("raw_content") if isinstance(result, dict) else result
        if raw is None:
            return None

        text = str(raw).strip()
        if not text or text.lower() == "null":
            return None

        if "{" not in text:
            logger.info(
                "Brave+AI extraction returned non-json text for barcode_ref=%s; "
                "treating as no product identified",
                redact_barcode(barcode),
            )
            return None

        parsed = extract_json(text)
        return parsed if isinstance(parsed, dict) else None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


def get_brave_search_nutrition_service(
    meal_generation_service: Any = None,
    macro_validation_service: Any = None,
) -> BraveSearchNutritionService | None:
    """Return a BraveSearchNutritionService if API key is configured, else None."""
    from src.infra.config.settings import settings

    if not settings.BRAVE_SEARCH_API_KEY:
        return None
    if not meal_generation_service or not macro_validation_service:
        return None
    return BraveSearchNutritionService(
        settings.BRAVE_SEARCH_API_KEY, meal_generation_service, macro_validation_service
    )
