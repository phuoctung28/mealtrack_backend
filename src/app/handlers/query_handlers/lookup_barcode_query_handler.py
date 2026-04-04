"""
LookupBarcodeQueryHandler - Handle barcode lookup with cascade:
DB -> FatSecret -> OpenFoodFacts -> Nutritionix -> Brave+AI -> AI estimate.
"""
import logging
from typing import Optional, Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService
from src.infra.adapters.fat_secret_service import FatSecretService, LANGUAGE_TO_REGION
from src.infra.repositories.food_reference_repository import FoodReferenceRepository

logger = logging.getLogger(__name__)

# GS1 barcode prefixes → country of origin (common entries)
GS1_COUNTRY_PREFIXES = {
    "890": "Vietnam", "893": "Vietnam",
    "880": "South Korea", "885": "Thailand",
    "888": "Singapore", "884": "Cambodia",
    "899": "Indonesia", "489": "Hong Kong",
    "471": "Taiwan", "480": "Philippines",
    "400": "Germany", "300": "France",
    "500": "United Kingdom", "800": "Italy",
    "450": "Japan", "840": "Spain",
}


def _get_country_from_barcode(barcode: str) -> str:
    """Determine country of origin from GS1 barcode prefix."""
    prefix3 = barcode[:3]
    if prefix3 in GS1_COUNTRY_PREFIXES:
        return GS1_COUNTRY_PREFIXES[prefix3]
    # Range-based prefixes
    if "690" <= prefix3 <= "699":
        return "China"
    if "000" <= prefix3 <= "019":
        return "United States"
    if "030" <= prefix3 <= "039":
        return "United States"
    if "300" <= prefix3 <= "379":
        return "France"
    if "400" <= prefix3 <= "440":
        return "Germany"
    return "Unknown"


@handles(LookupBarcodeQuery)
class LookupBarcodeQueryHandler(EventHandler[LookupBarcodeQuery, Optional[Dict[str, Any]]]):
    """Handler for looking up product by barcode with 6-step cascade."""

    def __init__(
        self,
        open_food_facts_service: OpenFoodFactsService,
        fat_secret_service: FatSecretService,
        food_reference_repository: FoodReferenceRepository,
        translation_service: Optional[Any] = None,
        nutritionix_service: Optional[Any] = None,
        brave_search_service: Optional[Any] = None,
        meal_generation_service: Optional[Any] = None,
        macro_validation_service: Optional[Any] = None,
    ):
        self.off = open_food_facts_service
        self.fat_secret = fat_secret_service
        self.repo = food_reference_repository
        self.translation_service = translation_service
        self.nutritionix = nutritionix_service
        self.brave_search = brave_search_service
        self.meal_gen = meal_generation_service
        self.macro_validator = macro_validation_service

    async def handle(self, query: LookupBarcodeQuery) -> Optional[Dict[str, Any]]:
        """Look up product by barcode with 6-step cascade."""

        # Step 1: Check local cache (DB)
        cached = self.repo.get_by_barcode(query.barcode)
        if cached:
            cached["source"] = "cache"
            return await self._maybe_translate(cached, query.language)

        # Step 2: Try FatSecret
        region = LANGUAGE_TO_REGION.get(query.language, "US")
        fat_secret_result = await self.fat_secret.get_product(
            query.barcode, region=region, language=query.language,
        )
        if fat_secret_result:
            fat_secret_result["source"] = "fatsecret"
            self._cache_result(fat_secret_result)
            return await self._maybe_translate(fat_secret_result, query.language)

        # Step 3: Try OpenFoodFacts
        off_result = await self.off.get_product(query.barcode)
        if off_result:
            off_result["source"] = "openfoodfacts"
            self._cache_result(off_result)
            return await self._maybe_translate(off_result, query.language)

        # Step 4: Try Nutritionix
        if self.nutritionix:
            nx_result = await self.nutritionix.get_product(query.barcode)
            if nx_result:
                nx_result["source"] = "nutritionix"
                self._cache_result(nx_result)
                return await self._maybe_translate(nx_result, query.language)

        # Step 5: Try Brave Search + Gemini extraction
        if self.brave_search:
            brave_result = await self.brave_search.get_product(
                query.barcode, query.language,
            )
            if brave_result:
                brave_result["source"] = "brave_search"
                self._cache_result(brave_result)
                return await self._maybe_translate(brave_result, query.language)

        # Step 6: AI estimation (last resort — don't cache unreliable data)
        estimate = await self._ai_estimate(query.barcode, query.language)
        if estimate:
            return estimate

        return None

    async def _ai_estimate(
        self, barcode: str, language: str,
    ) -> Optional[Dict[str, Any]]:
        """Estimate nutrition via Gemini when all other sources fail."""
        if not self.meal_gen:
            return None
        try:
            country = _get_country_from_barcode(barcode)
            system_prompt = (
                "You are a nutrition expert. A barcode was scanned but not found "
                "in any food database. Based on the barcode prefix (country of origin) "
                "and your knowledge, provide your best estimate of what this product "
                "might be and its approximate nutrition per 100g. "
                "Be conservative with estimates. "
                "Return ONLY valid JSON: "
                '{"name": "estimated product name", "brand": null, '
                '"protein_100g": float, "carbs_100g": float, "fat_100g": float, '
                '"fiber_100g": float, "sugar_100g": float}'
            )
            user_prompt = (
                f"Barcode: {barcode}\n"
                f"Country of origin: {country}\n"
                f"Language: {language}"
            )
            result = await self.meal_gen.generate_meal_plan(
                user_prompt, system_prompt, response_type="json",
            )
            if not result or not isinstance(result, dict):
                return None

            # Validate with macro validator if available
            if self.macro_validator:
                result = self.macro_validator.validate_and_correct(result)

            result["barcode"] = barcode
            result["source"] = "ai_estimate"
            result["is_estimate"] = True
            return result
        except Exception as e:
            logger.warning(f"AI estimation failed for barcode {barcode}: {e}")
            return None

    async def _maybe_translate(
        self, result: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        """Translate product name if non-English and translation service available."""
        if language == "en" or not self.translation_service:
            return result
        try:
            translated = await self.translation_service.translate_food_names(
                [result], language
            )
            return translated[0] if translated else result
        except Exception as e:
            logger.warning(f"Barcode product translation failed: {e}")
            return result

    def _cache_result(self, result: Dict[str, Any]) -> None:
        """Cache API result to food_reference table (fail silently on error)."""
        try:
            self.repo.upsert(result)
        except Exception as e:
            logger.warning(f"Failed to cache barcode {result.get('barcode')}: {e}")
