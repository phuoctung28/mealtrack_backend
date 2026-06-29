"""AI-backed value insights for meal details."""

import hashlib
import json
import logging
from typing import Any

from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.ports.cache_port import CachePort
from src.domain.ports.deepl_translation_port import DeepLTranslationPort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort
from src.domain.model.nutrition import Nutrition
from src.domain.services.meal_value_insight_contract import (
    IngredientValueInsight,
    MealValueInsights,
    ValueInsight,
    parse_ai_result,
    serialize_insights,
)
from src.observability import log_event

INSIGHT_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
logger = logging.getLogger(__name__)


SUPPORTED_INSIGHT_LANGUAGES = {"en", "vi", "es", "fr", "de", "ja", "zh"}


class MealValueInsightService:
    """Build practical, non-medical meal insights using backend AI."""

    def __init__(
        self,
        ai_manager: MealInsightAIPort | None = None,
        text_translation_service: DeepLTranslationPort | None = None,
    ) -> None:
        self._ai_manager = ai_manager
        self._text_translation_service = text_translation_service

    async def build_ai(
        self,
        *,
        dish_name: str | None,
        nutrition: Nutrition | None,
        ingredient_names_by_id: dict[str, str] | None = None,
        language: str = "en",
        user_context: dict[str, Any] | None = None,
        cache_service: CachePort | None = None,
    ) -> MealValueInsights | None:
        """Generate validated AI insights, falling back without blocking detail view."""
        if not nutrition:
            return None

        target_language = self._target_language(language)
        summary = self._summary(
            dish_name=dish_name,
            nutrition=nutrition,
            ingredient_names_by_id=ingredient_names_by_id or {},
            language="en",
            user_context=user_context or {},
        )
        cache_key = self._cache_key(summary)
        localized_cache_key = self._localized_cache_key(cache_key, target_language)
        if target_language != "en":
            cached_localized = await self._get_cached(
                cache_service, localized_cache_key
            )
            if cached_localized:
                return cached_localized

        cached = await self._get_cached(cache_service, cache_key)
        if cached:
            return await self._localize_insights(
                cached,
                target_language=target_language,
                cache_service=cache_service,
                localized_cache_key=localized_cache_key,
            )

        try:
            if self._ai_manager is None:
                raise RuntimeError("meal insight AI manager is not configured")
            result = await self._ai_manager.generate(
                purpose=ModelPurpose.GENERAL,
                prompt=self._prompt(summary),
                system_message=self._system_message(),
                response_type="json",
                max_tokens=450,
            )
            insights = parse_ai_result(result)
        except Exception as exc:
            logger.warning(
                "Meal value insight AI generation failed: %s", type(exc).__name__
            )
            log_event(
                "warning",
                "meal_value_insights.generation_failed",
                attributes={
                    "component": "meal_value_insight_service",
                    "failure_kind": type(exc).__name__,
                    "language": summary["language"],
                },
            )
            insights = None

        if insights is None:
            log_event(
                "info",
                "meal_value_insights.empty",
                attributes={
                    "component": "meal_value_insight_service",
                    "language": summary["language"],
                },
            )
            return None

        if insights:
            await self._set_cached(cache_service, cache_key, insights)
        return await self._localize_insights(
            insights,
            target_language=target_language,
            cache_service=cache_service,
            localized_cache_key=localized_cache_key,
        )

    async def get_cached_ai(
        self,
        *,
        dish_name: str | None,
        nutrition: Nutrition | None,
        ingredient_names_by_id: dict[str, str] | None = None,
        language: str = "en",
        user_context: dict[str, Any] | None = None,
        cache_service: CachePort | None = None,
    ) -> MealValueInsights | None:
        if not nutrition or cache_service is None:
            return None

        target_language = self._target_language(language)
        summary = self._summary(
            dish_name=dish_name,
            nutrition=nutrition,
            ingredient_names_by_id=ingredient_names_by_id or {},
            language="en",
            user_context=user_context or {},
        )
        cache_key = self._cache_key(summary)
        localized_cache_key = self._localized_cache_key(cache_key, target_language)
        if target_language != "en":
            cached_localized = await self._get_cached(
                cache_service, localized_cache_key
            )
            if cached_localized:
                return cached_localized

        cached = await self._get_cached(cache_service, cache_key)
        if cached is None:
            return None
        return await self._localize_insights(
            cached,
            target_language=target_language,
            cache_service=cache_service,
            localized_cache_key=localized_cache_key,
        )

    def version(
        self,
        *,
        dish_name: str | None,
        nutrition: Nutrition | None,
        ingredient_names_by_id: dict[str, str] | None = None,
        language: str = "en",
        user_context: dict[str, Any] | None = None,
    ) -> str | None:
        if not nutrition:
            return None
        target_language = self._target_language(language)
        summary = self._summary(
            dish_name=dish_name,
            nutrition=nutrition,
            ingredient_names_by_id=ingredient_names_by_id or {},
            language="en",
            user_context=user_context or {},
        )
        cache_key = self._cache_key(summary)
        if target_language == "en":
            return cache_key
        return self._localized_cache_key(cache_key, target_language)

    def _summary(
        self,
        *,
        dish_name: str | None,
        nutrition: Nutrition,
        ingredient_names_by_id: dict[str, str],
        language: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any]:
        macros = nutrition.macros
        ingredients = [
            {
                "id": str(item.id),
                "name": ingredient_names_by_id.get(str(item.id), item.name),
                "quantity": item.quantity,
                "unit": item.unit,
                "calories": item.calories,
                "protein_g": item.macros.protein,
                "carbs_g": item.macros.carbs,
                "fat_g": item.macros.fat,
                "fiber_g": item.macros.fiber,
                "sugar_g": item.macros.sugar,
                "confidence": item.confidence,
            }
            for item in (nutrition.food_items or [])[:8]
        ]
        ingredient_overview = self._ingredient_overview(ingredients)
        return {
            "dish_name": dish_name,
            "language": language,
            "macros": {
                "calories": nutrition.calories,
                "protein_g": macros.protein,
                "carbs_g": macros.carbs,
                "fat_g": macros.fat,
                "fiber_g": macros.fiber,
                "sugar_g": macros.sugar,
                "confidence": nutrition.confidence_score,
            },
            "ingredients": ingredients,
            "ingredient_overview": ingredient_overview,
            "risk_flags": self._risk_flags(macros, ingredient_overview),
            "user_context": user_context,
        }

    def _ingredient_overview(
        self, ingredients: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in ingredients:
            key = " ".join(str(item["name"]).casefold().split())
            entry = grouped.setdefault(
                key,
                {
                    "name": item["name"],
                    "count": 0,
                    "unit": item["unit"],
                    "total_quantity": 0.0,
                    "mixed_units": False,
                    "calories": 0.0,
                    "protein_g": 0.0,
                    "carbs_g": 0.0,
                    "fat_g": 0.0,
                    "fiber_g": 0.0,
                    "sugar_g": 0.0,
                },
            )
            entry["count"] += 1
            if entry["unit"] == item["unit"]:
                entry["total_quantity"] += item["quantity"]
            else:
                entry["mixed_units"] = True
            for field in (
                "calories",
                "protein_g",
                "carbs_g",
                "fat_g",
                "fiber_g",
                "sugar_g",
            ):
                entry[field] += item[field]

        overview = []
        for entry in grouped.values():
            overview.append(
                {
                    **entry,
                    "dominant_macro": self._dominant_macro(entry),
                    "repeated": entry["count"] > 1,
                    "large_portion": (
                        not entry["mixed_units"]
                        and entry["unit"] == "g"
                        and entry["total_quantity"] >= 250
                    ),
                }
            )
        return sorted(
            overview,
            key=lambda item: (item["repeated"], item["calories"]),
            reverse=True,
        )[:6]

    def _dominant_macro(self, item: dict[str, Any]) -> str:
        macros = {
            "protein": item["protein_g"] * 4,
            "carbs": item["carbs_g"] * 4,
            "fat": item["fat_g"] * 9,
        }
        return max(macros, key=macros.get)

    def _risk_flags(
        self,
        macros,
        ingredient_overview: list[dict[str, Any]],
    ) -> list[str]:
        flags: list[str] = []
        if macros.protein >= 120:
            flags.append("very_high_protein")
        if macros.carbs >= 120 and macros.fiber < 8:
            flags.append("high_carbs_low_fiber")
        for item in ingredient_overview:
            if item["repeated"]:
                flags.append(f"repeated_{item['dominant_macro']}_ingredient")
            if item["large_portion"]:
                flags.append(f"large_{item['dominant_macro']}_portion")
        return flags[:6]

    def _system_message(self) -> str:
        return (
            "You are Nutree's nutrition insight writer. Return only valid JSON. "
            "Give practical food guidance, not medical diagnosis. Avoid disease "
            "claims, treatment claims, and unsupported certainty."
        )

    def _prompt(self, summary: dict[str, Any]) -> str:
        return (
            "Generate concise meal value insights from this logged meal.\n"
            "Rules:\n"
            "- Output language must match language.\n"
            "- meal_bullets: max 2 items, each text <=120 characters.\n"
            "- ingredient_insights: max 2 key ingredients, one line each, text <=120 characters.\n"
            "- Text should mention relevant nutrients or macros when they explain the body effect.\n"
            "- Ingredient insights must call out what macro is high or low for that ingredient, then connect it to the body effect.\n"
            "- Use ingredient_overview to notice repeated ingredients or large portions; surface those as caution when they skew the meal.\n"
            "- Use risk_flags first. If risk_flags includes repeated_* or large_* for an ingredient, that ingredient insight must be caution.\n"
            "- Do not frame extreme protein, repeated protein ingredients, or very large portions as a benefit just because protein is usually useful.\n"
            "- For repeated or large portions, mention the repeated/large amount and the likely burden, such as heaviness, digestive load, or crowding out balance.\n"
            "- Each item should have one clear stance: benefit, caution, or neutral balance.\n"
            "- Avoid mixing helpful and harmful effects in the same item; do not use tradeoff wording like but, though, however, while, or although.\n"
            "- For benefit, describe the helpful effect only. For caution, describe the limiting or harmful effect only.\n"
            "- Do not include category labels inside text, such as Benefit:, Balance:, Caution:, or Warning:.\n"
            "- For each item, set highlights to exactly 1 exact substring from text worth spotlighting.\n"
            "- Each highlight must describe only how the meal may affect the body, such as fullness, steadier energy, digestion, recovery, hydration, or heaviness.\n"
            "- Do not include standalone nutrient or macro words like protein, carbs, fat, fiber, sugar, calories, or kcal in highlights.\n"
            "- The highlight must be localized, present verbatim in text, and <=40 characters.\n"
            "- category must be benefit, caution, or balance.\n"
            "- Ground claims in ingredients/macros/confidence. If uncertain, be generic or return empty arrays.\n"
            "- Keep total card copy near 280-320 characters or less.\n\n"
            "JSON shape:\n"
            '{"meal_bullets":[{"text":"...","category":"benefit","highlights":["..."]}],'
            '"ingredient_insights":[{"ingredient_name":"Egg","text":"...","category":"balance","highlights":["..."]}]}\n\n'
            f"Meal data:\n{json.dumps(summary, ensure_ascii=False)}"
        )

    def _cache_key(self, summary: dict[str, Any]) -> str:
        payload = json.dumps(summary, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return f"meal-value-insights:v8:{digest}"

    def _localized_cache_key(self, canonical_cache_key: str, language: str) -> str:
        return f"{canonical_cache_key}:lang:{language}"

    def _target_language(self, language: str) -> str:
        normalized = (language or "en").split("-")[0].lower()
        return normalized if normalized in SUPPORTED_INSIGHT_LANGUAGES else "en"

    async def _localize_insights(
        self,
        insights: MealValueInsights,
        *,
        target_language: str,
        cache_service: CachePort | None,
        localized_cache_key: str,
    ) -> MealValueInsights:
        if target_language == "en" or self._text_translation_service is None:
            return insights

        localized = await self._translate_insights(insights, target_language)
        if localized is None:
            return insights
        await self._set_cached(cache_service, localized_cache_key, localized)
        return localized

    async def _translate_insights(
        self,
        insights: MealValueInsights,
        target_language: str,
    ) -> MealValueInsights | None:
        texts: list[str] = []
        for item in insights.meal_bullets:
            texts.extend([item.text, *item.highlights[:1]])
        for item in insights.ingredient_insights:
            texts.extend([item.ingredient_name, item.text, *item.highlights[:1]])

        translated = await self._text_translation_service.translate_texts(
            texts,
            target_language,
        )
        while len(translated) < len(texts):
            translated.append(texts[len(translated)])
        if translated == texts:
            return None

        index = 0
        meal_bullets = []
        for item in insights.meal_bullets:
            highlight_count = len(item.highlights[:1])
            meal_bullets.append(
                ValueInsight(
                    text=translated[index],
                    category=item.category,
                    highlights=translated[index + 1 : index + 1 + highlight_count],
                )
            )
            index += 1 + highlight_count

        ingredient_insights = []
        for item in insights.ingredient_insights:
            highlight_count = len(item.highlights[:1])
            ingredient_insights.append(
                IngredientValueInsight(
                    ingredient_name=translated[index],
                    text=translated[index + 1],
                    category=item.category,
                    highlights=translated[index + 2 : index + 2 + highlight_count],
                )
            )
            index += 2 + highlight_count

        localized = MealValueInsights(
            meal_bullets=meal_bullets,
            ingredient_insights=ingredient_insights,
        )
        return parse_ai_result(serialize_insights(localized))

    async def _get_cached(self, cache_service: CachePort | None, key: str):
        if cache_service is None:
            return None
        cached = await cache_service.get(key)
        return parse_ai_result(cached)

    async def _set_cached(
        self,
        cache_service: CachePort | None,
        key: str,
        insights: MealValueInsights,
    ) -> None:
        if cache_service is None:
            return
        await cache_service.set(
            key,
            serialize_insights(insights),
            INSIGHT_CACHE_TTL_SECONDS,
        )
