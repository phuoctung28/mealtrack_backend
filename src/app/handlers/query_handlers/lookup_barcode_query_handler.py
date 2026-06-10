"""
LookupBarcodeQueryHandler - Handle barcode lookup with cascade:
DB -> FatSecret -> OpenFoodFacts -> Nutritionix -> Brave+AI -> AI estimate.
"""

import logging
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.infra.adapters.fat_secret_service import LANGUAGE_TO_REGION, FatSecretService
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService

logger = logging.getLogger(__name__)

# GS1 barcode prefixes → country of origin (common entries)
GS1_COUNTRY_PREFIXES = {
    "890": "Vietnam",
    "893": "Vietnam",
    "880": "South Korea",
    "885": "Thailand",
    "888": "Singapore",
    "884": "Cambodia",
    "899": "Indonesia",
    "489": "Hong Kong",
    "471": "Taiwan",
    "480": "Philippines",
    "400": "Germany",
    "300": "France",
    "500": "United Kingdom",
    "800": "Italy",
    "450": "Japan",
    "840": "Spain",
    "528": "Lebanon",
    "529": "Cyprus",
    "460": "Russia",
    "470": "Kyrgyzstan",
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
class LookupBarcodeQueryHandler(EventHandler[LookupBarcodeQuery, dict[str, Any] | None]):
    """Handler for looking up product by barcode with 6-step cascade."""

    def __init__(
        self,
        open_food_facts_service: OpenFoodFactsService,
        fat_secret_service: FatSecretService,
        food_reference_repository: Any | None = None,
        async_uow_factory: Any | None = None,
        translation_service: DeepLTextTranslationService | None = None,
        nutritionix_service: Any | None = None,
        brave_search_service: Any | None = None,
        meal_generation_service: Any | None = None,
        macro_validation_service: Any | None = None,
    ):
        self.off = open_food_facts_service
        self.fat_secret = fat_secret_service
        self.repo = food_reference_repository
        self.async_uow_factory = async_uow_factory
        self.translation_service = translation_service
        self.nutritionix = nutritionix_service
        self.brave_search = brave_search_service
        self.meal_gen = meal_generation_service
        self.macro_validator = macro_validation_service

    async def handle(self, query: LookupBarcodeQuery) -> dict[str, Any] | None:
        """Look up product by barcode with 6-step cascade."""
        # Track product name from partial matches (has name but no nutrition)
        partial_name: str | None = None

        # Step 1: Check local cache (DB)
        cached = await self._get_cached_product(query.barcode)
        if cached and self._has_nutrition(cached):
            logger.debug(f"[BARCODE-CASCADE] {query.barcode} → step 1 HIT (cache)")
            cached["source"] = "cache"
            return await self._maybe_translate(cached, query.language)
        if cached:
            partial_name = cached.get("name")
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 1 partial (name={partial_name}, no nutrition)"
            )

        # Step 2: Try FatSecret
        region = LANGUAGE_TO_REGION.get(query.language, "US")
        fat_secret_result = await self.fat_secret.get_product(
            query.barcode,
            region=region,
            language=query.language,
        )
        if fat_secret_result and self._has_nutrition(fat_secret_result):
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 2 HIT (fatsecret): {fat_secret_result.get('name')}"
            )
            fat_secret_result["source"] = "fatsecret"
            await self._cache_result(fat_secret_result)
            return await self._maybe_translate(fat_secret_result, query.language)
        if fat_secret_result:
            partial_name = partial_name or fat_secret_result.get("name")
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 2 partial (name={partial_name}, no nutrition)"
            )
        else:
            logger.debug(f"[BARCODE-CASCADE] {query.barcode} → step 2 MISS (fatsecret)")

        # Step 3: Try OpenFoodFacts
        off_result = await self.off.get_product(query.barcode)
        if off_result and self._has_nutrition(off_result):
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 3 HIT (openfoodfacts): {off_result.get('name')}"
            )
            off_result["source"] = "openfoodfacts"
            await self._cache_result(off_result)
            return await self._maybe_translate(off_result, query.language)
        if off_result:
            partial_name = partial_name or off_result.get("name")
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 3 partial (name={partial_name}, no nutrition)"
            )
        else:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 3 MISS (openfoodfacts)"
            )

        # Step 4: Try Nutritionix
        if self.nutritionix:
            nx_result = await self.nutritionix.get_product(query.barcode)
            if nx_result and self._has_nutrition(nx_result):
                logger.debug(
                    f"[BARCODE-CASCADE] {query.barcode} → step 4 HIT (nutritionix): {nx_result.get('name')}"
                )
                nx_result["source"] = "nutritionix"
                await self._cache_result(nx_result)
                return await self._maybe_translate(nx_result, query.language)
            if nx_result:
                partial_name = partial_name or nx_result.get("name")
        else:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 4 SKIP (nutritionix not configured)"
            )

        # Step 5: Try Brave Search + Gemini extraction
        brave_name: str | None = None
        if self.brave_search:
            brave_result = await self.brave_search.get_product(
                query.barcode,
                query.language,
                product_name=partial_name,
            )
            if brave_result:
                brave_name = brave_result.get("name")
                partial_name = partial_name or brave_name
        else:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 5 SKIP (brave not configured)"
            )

        # Step 5b: If Brave found a product name, search FatSecret by name for verified nutrition
        if brave_name:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 5b FatSecret name search: {brave_name}"
            )
            region = LANGUAGE_TO_REGION.get(query.language, "US")
            try:
                fs_results = await self.fat_secret.search_foods(
                    brave_name,
                    max_results=3,
                    region=region,
                    language=query.language,
                )
                if fs_results:
                    # Use first result with nutrition and a valid name
                    for fs_item in fs_results:
                        if self._has_nutrition(fs_item):
                            # Ensure name is set (FatSecret search can return null names)
                            if not fs_item.get("name"):
                                fs_item["name"] = brave_name
                            logger.debug(
                                f"[BARCODE-CASCADE] {query.barcode} → step 5b HIT (fatsecret name): {fs_item.get('name')}"
                            )
                            fs_item["source"] = "fatsecret"
                            fs_item["barcode"] = query.barcode
                            # Use brave_name as the display name (original brand name)
                            fs_item["name"] = brave_name
                            await self._cache_result(fs_item)
                            return fs_item  # Don't translate — brand names should stay as-is
            except Exception as e:
                logger.warning(f"FatSecret name search failed for '{brave_name}': {e}")

        # Step 5c: Return Brave estimate if available (editable)
        if brave_result and self._has_nutrition(brave_result):
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 5c using Brave estimate: {brave_name}"
            )
            brave_result["source"] = "brave_search"
            brave_result["barcode"] = query.barcode
            await self._cache_result(brave_result)
            return brave_result  # Don't translate — brand names should stay as-is
        elif brave_result:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 5 MISS (brave, no nutrition)"
            )
        else:
            logger.debug(
                f"[BARCODE-CASCADE] {query.barcode} → step 5 MISS (brave search)"
            )

        # Step 6: AI estimation (last resort — don't cache unreliable data)
        logger.debug(
            f"[BARCODE-CASCADE] {query.barcode} → step 6 AI estimation (partial_name={partial_name})"
        )
        estimate = await self._ai_estimate(query.barcode, query.language, partial_name)
        if estimate:
            return estimate

        return None

    @staticmethod
    def _has_nutrition(result: dict[str, Any]) -> bool:
        """Check if result has meaningful macro data (not all zeros/None)."""
        protein = result.get("protein_100g")
        carbs = result.get("carbs_100g")
        fat = result.get("fat_100g")
        # At least one macro must be a positive number
        for val in (protein, carbs, fat):
            if val is not None and val > 0:
                return True
        return False

    async def _ai_estimate(
        self,
        barcode: str,
        language: str,
        partial_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Estimate nutrition via Gemini when all other sources fail."""
        if not self.meal_gen:
            return None
        try:
            country = _get_country_from_barcode(barcode)
            system_prompt = (
                "You are a nutrition expert. This barcode was scanned in a food tracking app. "
                "Assume it IS a food product unless the product name clearly indicates otherwise "
                "(e.g. 'Dettol Soap', 'iPhone Charger', 'Paracetamol'). "
                "Based on the product name (if known), barcode prefix (country of origin), "
                "and your knowledge, estimate approximate nutrition per 100g. "
                "Be conservative with estimates. "
                "If the product name clearly indicates a non-food item, return "
                '{"is_food": false}. '
                "Otherwise return ONLY valid JSON: "
                '{"is_food": true, "name": "product name", "brand": null, '
                '"protein_100g": float, "carbs_100g": float, "fat_100g": float, '
                '"fiber_100g": float, "sugar_100g": float}'
            )
            name_hint = f"Product name: {partial_name}\n" if partial_name else ""
            user_prompt = (
                f"{name_hint}"
                f"Barcode: {barcode}\n"
                f"Country of origin: {country}\n"
                f"Language: {language}"
            )
            logger.debug(
                f"AI estimation for {barcode}: country={country}, "
                f"partial_name={partial_name}, prompt_len={len(user_prompt)}"
            )
            result = await self.meal_gen.generate_meal_plan_async(
                user_prompt,
                system_prompt,
                response_type="json",
                max_tokens=500,
                model_purpose="barcode",
            )
            if not result or not isinstance(result, dict):
                return None

            # Non-food item detected by AI
            if not result.get("is_food", True):
                logger.debug(f"Non-food item detected for barcode {barcode}")
                return None

            # Validate with macro validator if available
            if self.macro_validator:
                result = self.macro_validator.validate_and_correct(result)

            result["barcode"] = barcode
            result["source"] = "ai_estimate"
            result["is_estimate"] = True
            # Ensure name is never null (required by response schema)
            if not result.get("name"):
                result["name"] = partial_name or f"Unknown product ({country})"
            return result
        except Exception as e:
            logger.warning(f"AI estimation failed for barcode {barcode}: {e}")
            return None

    async def _maybe_translate(
        self, result: dict[str, Any], language: str
    ) -> dict[str, Any]:
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

    async def _get_cached_product(self, barcode: str) -> dict[str, Any] | None:
        if self.async_uow_factory is not None:
            async with self.async_uow_factory() as uow:
                return await uow.food_references.get_by_barcode(barcode)
        if self.repo is None:
            return None
        cached = self.repo.get_by_barcode(barcode)
        if hasattr(cached, "__await__"):
            return await cached
        return cached

    async def _cache_result(self, result: dict[str, Any]) -> None:
        """Cache API result to food_reference table (fail silently on error)."""
        if not result.get("name"):
            logger.warning(
                f"Skipping cache for barcode {result.get('barcode')}: name is required"
            )
            return
        try:
            if self.async_uow_factory is not None:
                async with self.async_uow_factory() as uow:
                    await uow.food_references.upsert(result)
                return
            if self.repo is None:
                return
            upserted = self.repo.upsert(result)
            if hasattr(upserted, "__await__"):
                await upserted
        except Exception as e:
            logger.warning(f"Failed to cache barcode {result.get('barcode')}: {e}")
