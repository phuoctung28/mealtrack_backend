"""Search foods for manual logging using the configured provider."""

import hashlib
import logging
import re
from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.app.services.food_name_localizer import (
    translate_food_texts,
    translated_values,
    translation_is_cacheable,
)
from src.domain.model.translation_result import TranslationOutcome
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort
from src.domain.ports.food_reference_repository_port import (
    FoodReferenceSearchProjection,
)
from src.domain.services.nutrition_integrity_policy import NutritionIntegrityError
from src.observability import distribution_metric, increment_metric

logger = logging.getLogger(__name__)


@handles(SearchFoodsQuery)
class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, dict[str, Any]]):
    """Handler for FatSecret-backed food search and autocomplete."""

    def __init__(
        self,
        cache_service,
        mapping_service: FoodMappingServicePort,
        fat_secret_service: Any | None = None,
        translation_service: Any | None = None,
        local_search: Callable[[str, str, int], Any] | None = None,
        integrity_context: Callable[[], Any] | None = None,
    ):
        self.cache_service = cache_service
        self.mapping_service = mapping_service
        self.fat_secret_service = fat_secret_service
        self.translation_service = translation_service
        self.local_search = local_search
        self.integrity_context = integrity_context

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
        cache_context = await self._get_integrity_context()

        # Integrity-controlled caches are versioned by policy and generation;
        # retain the query as the stable key for that namespace.
        cache_key = (
            event.query
            if self.integrity_context is not None
            else self._cache_key(event.query, language)
        )
        cached = None
        if self.integrity_context is None:
            try:
                cached = await self.cache_service.get_cached_search(cache_key)
            except Exception:
                logger.warning("food search cache read failed", exc_info=True)
        elif cache_context is not None:
            try:
                cached = await self.cache_service.get_cached_search(
                    cache_key,
                    policy_version=str(cache_context["policy_version"]),
                    generation=int(cache_context["generation"]),
                )
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

        canonical_query = await self._canonical_query(event.query, language)
        processed_raw = await self._search_local(
            event,
            query=canonical_query,
            region="US" if is_non_english else self._region_for_language(language),
        )
        local_count = len(processed_raw)
        remaining_limit = max(event.limit - len(processed_raw), 0)
        provider_attempted = bool(self.fat_secret_service and remaining_limit > 0)

        if self.fat_secret_service and remaining_limit > 0:
            if is_non_english:
                processed_raw = await self._search_localized(
                    canonical_query,
                    remaining_limit,
                    language,
                    cache_key,
                    processed_raw,
                    cache_context,
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
                        await self._cache_search(
                            cache_key, processed_raw, cache_context
                        )
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
        cache_context: Mapping[str, int | str] | None,
    ) -> list[dict[str, Any]]:
        """Acquire canonical provider data, then localize complete results."""
        try:
            results = await self.fat_secret_service.search_foods(
                query, max_results=limit
            )
            if results:
                merged = self._merge_search_results(
                    local_raw, results, len(local_raw) + limit
                )
                return await self._localize_results(
                    merged,
                    language=language,
                    cache_key=cache_key,
                    cache_context=cache_context,
                )
        except Exception:
            logger.warning("fatsecret canonical search failed", exc_info=True)
        return local_raw

    async def _canonical_query(self, query: str, language: str) -> str:
        if language == "en" or self.translation_service is None:
            return query
        result = await translate_food_texts(
            [query],
            source_language=language,
            target_language="en",
            translation_service=self.translation_service,
        )
        if result.outcome is TranslationOutcome.TRANSLATED and result.texts:
            return result.texts[0]
        return query

    async def _localize_results(
        self,
        results: list[dict[str, Any]],
        *,
        language: str,
        cache_key: str,
        cache_context: Mapping[str, int | str] | None,
    ) -> list[dict[str, Any]]:
        if not results or self.translation_service is None:
            return results
        names: list[str] = []
        for item in results:
            name = str(item.get("description") or item.get("name") or "")
            if name and name not in names:
                names.append(name)
        if not names:
            return results
        result = await translate_food_texts(
            names,
            target_language=language,
            translation_service=self.translation_service,
        )
        translated = dict(zip(names, translated_values(names, result), strict=False))
        localized = []
        for item in results:
            localized_item = item.copy()
            original = str(
                localized_item.get("description") or localized_item.get("name") or ""
            )
            if original in translated:
                if "description" in localized_item:
                    localized_item["description"] = translated[original]
                if "name" in localized_item:
                    localized_item["name"] = translated[original]
            localized.append(localized_item)
        if translation_is_cacheable(result):
            await self._cache_search(cache_key, localized, cache_context)
        return localized

    async def _cache_search(
        self,
        cache_key: str,
        results: list[dict[str, Any]],
        cache_context: Mapping[str, int | str] | None,
    ) -> None:
        if self.integrity_context is not None and cache_context is None:
            return
        try:
            if self.integrity_context is None:
                await self.cache_service.cache_search(cache_key, results)
            else:
                await self.cache_service.cache_search(
                    cache_key,
                    results,
                    policy_version=str(cache_context["policy_version"]),
                    generation=int(cache_context["generation"]),
                )
        except Exception:
            logger.warning("food search cache write failed", exc_info=True)

    async def _get_integrity_context(self) -> Mapping[str, int | str] | None:
        if self.integrity_context is None:
            return None
        try:
            value = await self.integrity_context()
            if not isinstance(value, Mapping):
                raise TypeError("integrity context must be a mapping")
            if "policy_version" not in value or "generation" not in value:
                raise ValueError("integrity context is incomplete")
            return value
        except Exception:
            logger.warning("food integrity control read failed", exc_info=True)
            return None

    async def _search_local(
        self,
        event: SearchFoodsQuery,
        *,
        query: str | None = None,
        region: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.local_search:
            return []
        try:
            projections = await self.local_search(
                query if query is not None else event.query,
                region or self._region_for_language(event.language),
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
            "origin": "local",
            "source_namespace": item.source_namespace or "food_reference",
            "source_food_id": item.source_food_id or str(item.id),
            "food_id": f"food_reference:{item.id}",
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
        local_names = {
            str(item.get("name_normalized") or item.get("description") or "")
            .strip()
            .lower()
            for item in local_raw
        }
        for item in provider_raw:
            item.setdefault("source", "fatsecret")
            if not item.get("source_food_id") and not item.get("food_id"):
                provider_name = (
                    str(item.get("name_normalized") or item.get("description") or "")
                    .strip()
                    .lower()
                )
                if provider_name in local_names:
                    continue
            key = self._search_result_key(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break
        return merged[:limit]

    def _search_result_key(self, item: dict[str, Any]) -> str:
        namespace = item.get("source_namespace")
        source_id = item.get("source_food_id")
        if namespace and source_id is not None:
            return f"identity:{str(namespace).strip().lower()}:{str(source_id).strip()}"
        if item.get("food_reference_id") is not None:
            return f"identity:food_reference:{item['food_reference_id']}"
        food_id = item.get("food_id")
        if food_id and ":" in str(food_id):
            return f"identity:{str(food_id).strip().lower()}"
        source = str(item.get("source") or "").strip().lower()
        if source in {"fatsecret", "openfoodfacts", "provider"} and food_id:
            return f"identity:{source}:{str(food_id).strip()}"
        normalized = item.get("name_normalized")
        if normalized:
            return str(normalized).strip().lower()
        return str(item.get("description") or item.get("name") or "").strip().lower()

    def _region_for_language(self, language: str) -> str:
        if language == "vi":
            return "VN"
        return "US"

    @staticmethod
    def _cache_key(query: str, language: str) -> str:
        normalized = re.sub(r"\s+", " ", query.strip().lower())
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"food-search:v2:{language}:{digest}"

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
            name_key = self._search_result_key(
                {**item, "description": capitalized_name}
            )

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
