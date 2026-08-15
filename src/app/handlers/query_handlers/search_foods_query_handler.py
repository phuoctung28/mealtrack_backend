"""Search foods for manual logging using the configured provider."""

import logging
from collections.abc import Callable
from time import perf_counter
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.ports.food_reference_repository_port import (
    FoodReferenceSearchProjection,
)
from src.domain.services.food_mapping_service import FoodMappingService
from src.domain.services.nutrition_integrity_policy import NutritionIntegrityError
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.observability import distribution_metric, increment_metric

logger = logging.getLogger(__name__)


@handles(SearchFoodsQuery)
class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, dict[str, Any]]):
    """Handler for FatSecret-backed food search and autocomplete."""

    def __init__(
        self,
        cache_service,
        mapping_service: FoodMappingService,
        fat_secret_service: Any | None = None,
        translation_service: DeepLTextTranslationService | None = None,
        local_search: Callable[[str, str, int], Any] | None = None,
    ):
        self.cache_service = cache_service
        self.mapping_service = mapping_service
        self.fat_secret_service = fat_secret_service
        self.translation_service = translation_service
        self.local_search = local_search

    async def handle(self, event: SearchFoodsQuery) -> dict[str, Any]:
        started = perf_counter()
        if not event.query or not event.query.strip():
            self._record_search_metrics(
                started,
                source="local",
                language=event.language,
                status="empty",
            )
            return {"results": [], "query": event.query, "total": 0}

        language = event.language
        is_non_english = language != "en"

        # Language-aware cache key (prefixed to avoid collisions)
        cache_key = f"{language}:{event.query}" if is_non_english else event.query
        cached = None
        try:
            cached = await self.cache_service.get_cached_search(cache_key)
        except Exception:
            logger.warning("food search cache read failed", exc_info=True)
        if cached is not None:
            processed_cached = self._process_search_results(cached)
            processed_cached = processed_cached[: event.limit]
            for item in processed_cached:
                if "source" not in item:
                    item["source"] = "fatsecret"
            mapped = self._map_search_items(processed_cached)
            self._record_search_metrics(
                started,
                source="cache",
                language=language,
                status="success" if mapped else "empty",
            )
            return {"results": mapped, "query": event.query, "total": len(mapped)}

        processed_raw = await self._search_local(event)
        local_count = len(processed_raw)
        remaining_limit = max(event.limit - len(processed_raw), 0)
        provider_attempted = bool(self.fat_secret_service and remaining_limit > 0)

        if self.fat_secret_service and remaining_limit > 0:
            if is_non_english:
                processed_raw = await self._search_localized(
                    event.query,
                    remaining_limit,
                    language,
                    cache_key,
                    processed_raw,
                )
            else:
                try:
                    fs_results = await self.fat_secret_service.search_foods(
                        event.query, max_results=remaining_limit
                    )
                    processed_raw = self._merge_search_results(
                        processed_raw,
                        fs_results,
                        event.limit,
                    )
                    if fs_results:
                        await self._cache_search(cache_key, processed_raw)
                except Exception:
                    logger.warning("fatsecret search failed", exc_info=True)

        mapped = self._map_search_items(processed_raw)
        self._record_search_metrics(
            started,
            source=self._source_label(local_count, len(processed_raw)),
            language=language,
            status=self._status_label(
                result_count=len(mapped),
                local_count=local_count,
                provider_attempted=provider_attempted,
            ),
        )
        return {"results": mapped, "query": event.query, "total": len(mapped)}

    def _map_search_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        mapped: list[dict[str, Any]] = []
        for item in items:
            try:
                mapped.append(self.mapping_service.map_search_item(item))
            except NutritionIntegrityError as exc:
                logger.info(
                    "food search item rejected by nutrition integrity policy: %s",
                    exc.result.reason_code,
                )
        return mapped

    async def _search_localized(
        self,
        query: str,
        limit: int,
        language: str,
        cache_key: str,
        local_raw: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Search with localization: try native region first, fallback only if empty."""
        from src.infra.adapters.fat_secret_service import LANGUAGE_TO_REGION

        region = LANGUAGE_TO_REGION.get(language, "US")

        # Step 1: Try fatsecret with localized region — cache and return immediately if anything found
        try:
            results = await self.fat_secret_service.search_foods(
                query,
                max_results=limit,
                region=region,
                language=language,
            )
            if results:
                logger.debug(
                    f"fatsecret region={region} returned {len(results)} results"
                )
                merged = self._merge_search_results(
                    local_raw, results, len(local_raw) + limit
                )
                await self._cache_search(cache_key, merged)
                return merged
        except Exception:
            logger.warning(f"fatsecret region={region} failed", exc_info=True)

        # Step 2: Translation fallback — only on true empty response from localized search
        if not self.translation_service:
            try:
                results = await self.fat_secret_service.search_foods(
                    query, max_results=limit
                )
                if results:
                    merged = self._merge_search_results(
                        local_raw,
                        results,
                        len(local_raw) + limit,
                    )
                    await self._cache_search(cache_key, merged)
                    return merged
                return local_raw
            except Exception:
                return local_raw

        try:
            translated_queries = await self.translation_service.translate_to_english(
                [query], language
            )
        except Exception:
            logger.warning("translation fallback failed", exc_info=True)
            return local_raw
        translated_query = translated_queries[0] if translated_queries else query

        logger.info(f"Translation fallback: '{query}' -> '{translated_query}'")

        try:
            results = await self.fat_secret_service.search_foods(
                translated_query, max_results=limit
            )
        except Exception:
            logger.warning("fatsecret EN fallback failed", exc_info=True)
            return []

        if not results:
            return local_raw

        results = await self.translation_service.translate_food_names(results, language)
        merged = self._merge_search_results(local_raw, results, len(local_raw) + limit)
        await self._cache_search(cache_key, merged)
        return merged

    async def _cache_search(
        self, cache_key: str, results: list[dict[str, Any]]
    ) -> None:
        try:
            await self.cache_service.cache_search(cache_key, results)
        except Exception:
            logger.warning("food search cache write failed", exc_info=True)

    async def _search_local(self, event: SearchFoodsQuery) -> list[dict[str, Any]]:
        if not self.local_search:
            return []
        try:
            projections = await self.local_search(
                event.query,
                self._region_for_language(event.language),
                event.limit,
            )
        except Exception:
            logger.warning("local food_reference search failed", exc_info=True)
            return []
        return [self._local_projection_to_raw(item) for item in projections]

    def _local_projection_to_raw(
        self,
        item: FoodReferenceSearchProjection,
    ) -> dict[str, Any]:
        return {
            "source": "food_reference",
            "food_reference_id": item.id,
            "description": item.name,
            "name_normalized": item.name_normalized,
            "brand": item.brand,
            "provider_source": item.source,
            "is_verified": item.is_verified,
            "serving_description": item.serving_size,
            "allowed_units": item.allowed_units,
            "protein_100g": item.protein_100g,
            "carbs_100g": item.carbs_100g,
            "fat_100g": item.fat_100g,
            "fiber_100g": item.fiber_100g,
            "sugar_100g": item.sugar_100g,
        }

    def _merge_search_results(
        self,
        local_raw: list[dict[str, Any]],
        provider_raw: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        merged = list(local_raw)
        seen = {self._search_result_key(item) for item in merged}
        for item in provider_raw:
            item.setdefault("source", "fatsecret")
            key = self._search_result_key(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break
        return merged[:limit]

    def _search_result_key(self, item: dict[str, Any]) -> str:
        normalized = item.get("name_normalized")
        if normalized:
            return str(normalized).strip().lower()
        return str(item.get("description") or item.get("name") or "").strip().lower()

    def _region_for_language(self, language: str) -> str:
        if language == "vi":
            return "VN"
        return "US"

    def _source_label(self, local_count: int, result_count: int) -> str:
        if local_count and result_count > local_count:
            return "mixed"
        if local_count:
            return "local"
        return "provider"

    def _status_label(
        self,
        *,
        result_count: int,
        local_count: int,
        provider_attempted: bool,
    ) -> str:
        if result_count == 0:
            return "empty"
        if provider_attempted and local_count > 0 and result_count == local_count:
            return "degraded"
        return "success"

    def _record_search_metrics(
        self,
        started: float,
        *,
        source: str,
        language: str,
        status: str,
    ) -> None:
        attributes = {
            "operation": "search",
            "source": source,
            "language": language,
            "status": status,
        }
        distribution_metric(
            "food_search.operation.latency_ms",
            (perf_counter() - started) * 1000,
            unit="millisecond",
            attributes=attributes,
        )
        increment_metric("food_search.requests", attributes=attributes)

    def _process_search_results(
        self, raw_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process search results: deduplicate and capitalize names."""
        if not raw_results:
            return raw_results

        seen_names = set()
        processed_results = []

        for item in raw_results:
            original_name = item.get("description", "")
            capitalized_name = self._capitalize_food_name(original_name)
            name_key = capitalized_name.lower().strip()

            if name_key not in seen_names:
                seen_names.add(name_key)
                processed_item = item.copy()
                processed_item["description"] = capitalized_name
                processed_results.append(processed_item)

        return processed_results

    def _capitalize_food_name(self, name: str) -> str:
        """Properly capitalize food names."""
        if not name:
            return name

        parts = []
        for part in name.split(","):
            words = []
            for word in part.strip().split():
                word_lower = word.lower()
                if word_lower in [
                    "and",
                    "or",
                    "with",
                    "in",
                    "on",
                    "of",
                    "the",
                    "a",
                    "an",
                ]:
                    words.append(word_lower if words else word.capitalize())
                else:
                    words.append(word.capitalize())

            if words:
                parts.append(" ".join(words))

        return ", ".join(parts)
