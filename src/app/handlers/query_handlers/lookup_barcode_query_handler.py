"""
LookupBarcodeQueryHandler - Handle barcode lookup with cascade:
DB -> FatSecret -> OpenFoodFacts -> USDA FDC -> Brave identity/estimate -> AI estimate.
"""

import logging
import time
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.domain.services.barcode.barcode_logging import redact_barcode
from src.domain.services.barcode.barcode_nutrition_validator import (
    validate_barcode_nutrition,
)
from src.domain.services.prompts.system_prompts import SystemPrompts
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.infra.adapters.fat_secret_service import LANGUAGE_TO_REGION, FatSecretService
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService

logger = logging.getLogger(__name__)

TRUSTED_CACHE_SOURCES = {"fatsecret", "openfoodfacts", "usda_fdc", "cache", None}


def _gs1_prefix_hint(barcode: str) -> str:
    return barcode[:3] if len(barcode) >= 3 else "unknown"


@handles(LookupBarcodeQuery)
class LookupBarcodeQueryHandler(EventHandler[LookupBarcodeQuery, dict[str, Any] | None]):
    """Handler for looking up product by barcode with fallback providers."""

    def __init__(
        self,
        open_food_facts_service: OpenFoodFactsService,
        fat_secret_service: FatSecretService,
        food_reference_repository: Any | None = None,
        async_uow_factory: Any | None = None,
        translation_service: DeepLTextTranslationService | None = None,
        brave_search_service: Any | None = None,
        meal_generation_service: Any | None = None,
        macro_validation_service: Any | None = None,
        food_data_service: Any | None = None,
        food_mapping_service: Any | None = None,
    ):
        self.off = open_food_facts_service
        self.fat_secret = fat_secret_service
        self.repo = food_reference_repository
        self.async_uow_factory = async_uow_factory
        self.translation_service = translation_service
        self.brave_search = brave_search_service
        self.meal_gen = meal_generation_service
        self.macro_validator = macro_validation_service
        self.food_data_service = food_data_service
        self.food_mapping_service = food_mapping_service

    async def handle(self, query: LookupBarcodeQuery) -> dict[str, Any] | None:
        """Look up product by barcode with provider cascade."""
        started_at = time.perf_counter()
        miss_reasons: list[str] = []
        scanned_barcode = query.scanned_barcode or query.barcode
        barcode_ref = redact_barcode(scanned_barcode)
        aliases = query.aliases or (query.barcode,)

        def elapsed_ms() -> int:
            return round((time.perf_counter() - started_at) * 1000)

        def log_hit(source: str, result: dict[str, Any]) -> None:
            logger.info(
                "Barcode lookup hit barcode_ref=%s source=%s provider_source=%s "
                "elapsed_ms=%d name_present=%s is_estimate=%s",
                barcode_ref,
                source,
                result.get("provider_source") or result.get("source"),
                elapsed_ms(),
                bool(result.get("name")),
                bool(result.get("is_estimate")),
            )

        partial_name: str | None = None

        cached = await self._get_cached_product(aliases)
        if cached and self._has_nutrition(cached) and self._is_trusted_cached_row(cached):
            provider_source = cached.get("source")
            cached["provider_source"] = provider_source
            cached["source"] = "cache"
            cached["barcode"] = scanned_barcode
            log_hit("cache", cached)
            return await self._maybe_translate(cached, query.language)
        if cached:
            partial_name = cached.get("name")
            reason = (
                "cache_untrusted_source"
                if self._has_nutrition(cached)
                else "cache_partial_no_nutrition"
            )
            miss_reasons.append(reason)
            logger.debug(
                "[BARCODE-CASCADE] barcode_ref=%s step=cache reason=%s",
                barcode_ref,
                reason,
            )
        else:
            miss_reasons.append("cache_empty")

        region = LANGUAGE_TO_REGION.get(query.language, "US")
        fat_secret_result = await self._first_barcode_hit(
            aliases,
            lambda alias: self.fat_secret.get_product(
                alias,
                region=region,
                language=query.language,
            ),
        )
        if fat_secret_result and self._has_nutrition(fat_secret_result):
            result = self._trusted_provider_result(
                fat_secret_result, query.barcode, scanned_barcode, "fatsecret"
            )
            await self._cache_result(result, cache_barcode=query.barcode)
            log_hit("fatsecret", result)
            return await self._maybe_translate(result, query.language)
        if fat_secret_result:
            partial_name = partial_name or fat_secret_result.get("name")
            miss_reasons.append("fatsecret_partial_no_nutrition")
        else:
            miss_reasons.append("fatsecret_empty")

        off_result = await self._first_barcode_hit(aliases, self.off.get_product)
        if off_result and self._has_nutrition(off_result):
            result = self._trusted_provider_result(
                off_result, query.barcode, scanned_barcode, "openfoodfacts"
            )
            await self._cache_result(result, cache_barcode=query.barcode)
            log_hit("openfoodfacts", result)
            return await self._maybe_translate(result, query.language)
        if off_result:
            partial_name = partial_name or off_result.get("name")
            miss_reasons.append("openfoodfacts_partial_no_nutrition")
        else:
            miss_reasons.append("openfoodfacts_empty")

        fdc_result = await self._get_fdc_product(aliases, query.barcode, scanned_barcode)
        if fdc_result and self._has_nutrition(fdc_result):
            await self._cache_result(fdc_result, cache_barcode=query.barcode)
            log_hit("usda_fdc", fdc_result)
            return await self._maybe_translate(fdc_result, query.language)
        miss_reasons.append("usda_fdc_empty")

        brave_name: str | None = None
        brave_result: dict[str, Any] | None = None
        if self.brave_search:
            brave_result = await self.brave_search.get_product(
                scanned_barcode,
                query.language,
                product_name=partial_name,
            )
            if brave_result:
                brave_name = brave_result.get("name")
                partial_name = partial_name or brave_name
                if not self._has_nutrition(brave_result):
                    miss_reasons.append("brave_partial_no_nutrition")
        else:
            miss_reasons.append("brave_not_configured")

        if brave_name:
            estimate = await self._fatsecret_name_estimate(
                brave_name, region, query.language, scanned_barcode, barcode_ref
            )
            if estimate:
                log_hit("fatsecret_name_estimate", estimate)
                return estimate

        if brave_result and self._has_nutrition(brave_result):
            estimate = self._estimate_result(brave_result, scanned_barcode, "brave_search")
            log_hit("brave_search", estimate)
            return estimate
        if self.brave_search and not brave_result:
            miss_reasons.append("brave_empty")

        estimate = await self._ai_estimate(scanned_barcode, query.language, partial_name)
        if estimate:
            log_hit("ai_estimate", estimate)
            return estimate

        miss_reasons.append("ai_estimate_empty")
        logger.warning(
            "Barcode lookup miss barcode_ref=%s language=%s elapsed_ms=%d "
            "miss_reasons=%s partial_name_present=%s",
            barcode_ref,
            query.language,
            elapsed_ms(),
            ",".join(miss_reasons),
            bool(partial_name),
        )
        return None

    @staticmethod
    def _has_nutrition(result: dict[str, Any]) -> bool:
        """Check if result has meaningful macro data (not all zeros/None)."""
        for key in ("protein_100g", "carbs_100g", "fat_100g"):
            val = result.get(key)
            if val is not None and val > 0:
                return True
        return False

    @staticmethod
    def _is_trusted_cached_row(result: dict[str, Any]) -> bool:
        return bool(result.get("is_verified")) or result.get("source") in TRUSTED_CACHE_SOURCES

    async def _first_barcode_hit(self, aliases, fetch):
        for alias in aliases:
            result = await fetch(alias)
            if result:
                return result
        return None

    async def _get_fdc_product(
        self,
        aliases: tuple[str, ...],
        canonical_barcode: str,
        scanned_barcode: str,
    ) -> dict[str, Any] | None:
        if not self.food_data_service or not self.food_mapping_service:
            return None
        try:
            raw = await self.food_data_service.get_branded_food_by_gtin(list(aliases))
        except Exception as exc:
            logger.warning("USDA FDC barcode lookup failed: %s", type(exc).__name__)
            return None
        if not raw:
            return None
        mapped = self.food_mapping_service.map_fdc_barcode_product(
            raw, barcode=canonical_barcode
        )
        mapped["barcode"] = scanned_barcode
        return validate_barcode_nutrition(mapped)

    async def _fatsecret_name_estimate(
        self,
        brave_name: str,
        region: str,
        language: str,
        scanned_barcode: str,
        barcode_ref: str,
    ) -> dict[str, Any] | None:
        try:
            fs_results = await self.fat_secret.search_foods(
                brave_name,
                max_results=3,
                region=region,
                language=language,
            )
        except Exception as exc:
            logger.warning(
                "FatSecret name estimate failed barcode_ref=%s error=%s",
                barcode_ref,
                type(exc).__name__,
            )
            return None

        for item in fs_results or []:
            if self._has_nutrition(item):
                item["name"] = brave_name or item.get("name")
                return self._estimate_result(item, scanned_barcode, "fatsecret_name_search")
        return None

    def _trusted_provider_result(
        self,
        result: dict[str, Any],
        canonical_barcode: str,
        scanned_barcode: str,
        source: str,
    ) -> dict[str, Any]:
        payload = validate_barcode_nutrition(result)
        payload["barcode"] = scanned_barcode
        payload["cache_barcode"] = canonical_barcode
        payload["source"] = source
        payload["provider_source"] = source
        payload["is_verified"] = True
        payload["is_estimate"] = False
        return payload

    @staticmethod
    def _estimate_result(
        result: dict[str, Any],
        scanned_barcode: str,
        source: str,
    ) -> dict[str, Any]:
        payload = validate_barcode_nutrition(result)
        payload["barcode"] = scanned_barcode
        payload["source"] = source
        payload["provider_source"] = source
        payload["is_estimate"] = True
        payload["is_verified"] = False
        return payload

    async def _ai_estimate(
        self,
        barcode: str,
        language: str,
        partial_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Estimate nutrition via AI when all other sources fail."""
        if not self.meal_gen:
            return None
        try:
            system_prompt = SystemPrompts.BARCODE_AI_ESTIMATE
            name_hint = f"Product name: {partial_name}\n" if partial_name else ""
            user_prompt = (
                f"{name_hint}"
                f"Barcode: {barcode}\n"
                f"GS1 prefix allocation hint: {_gs1_prefix_hint(barcode)}\n"
                f"Language: {language}"
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

            if not result.get("is_food", True):
                logger.debug(
                    "Non-food item detected for barcode_ref=%s", redact_barcode(barcode)
                )
                return None

            payload = self._estimate_result(result, barcode, "ai_estimate")
            if not payload.get("name"):
                payload["name"] = partial_name or "Unknown product"
            return payload
        except Exception as exc:
            logger.warning(
                "AI estimation failed for barcode_ref=%s error=%s",
                redact_barcode(barcode),
                type(exc).__name__,
            )
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
        except Exception as exc:
            logger.warning("Barcode product translation failed: %s", type(exc).__name__)
            return result

    async def _get_cached_product(self, aliases: tuple[str, ...]) -> dict[str, Any] | None:
        candidates: list[dict[str, Any]] = []
        for barcode in aliases:
            cached = await self._get_cached_product_by_barcode(barcode)
            if cached:
                candidates.append(cached)
        if not candidates:
            return None
        candidates.sort(
            key=lambda row: (
                not bool(row.get("is_verified")),
                row.get("source") not in TRUSTED_CACHE_SOURCES,
            )
        )
        return candidates[0]

    async def _get_cached_product_by_barcode(
        self, barcode: str
    ) -> dict[str, Any] | None:
        if self.async_uow_factory is not None:
            async with self.async_uow_factory() as uow:
                return await uow.food_references.get_by_barcode(barcode)
        if self.repo is None:
            return None
        cached = self.repo.get_by_barcode(barcode)
        if hasattr(cached, "__await__"):
            return await cached
        return cached

    async def _cache_result(
        self, result: dict[str, Any], cache_barcode: str | None = None
    ) -> None:
        """Cache verified API result to food_reference table."""
        if not result.get("name"):
            logger.warning(
                "Skipping cache for barcode_ref=%s: name is required",
                redact_barcode(result.get("barcode")),
            )
            return
        payload = dict(result)
        if cache_barcode:
            payload["barcode"] = cache_barcode
        payload.pop("cache_barcode", None)
        try:
            if self.async_uow_factory is not None:
                async with self.async_uow_factory() as uow:
                    await uow.food_references.upsert(payload)
                return
            if self.repo is None:
                return
            upserted = self.repo.upsert(payload)
            if hasattr(upserted, "__await__"):
                await upserted
        except Exception as exc:
            logger.warning(
                "Failed to cache barcode_ref=%s error=%s",
                redact_barcode(payload.get("barcode")),
                type(exc).__name__,
            )
