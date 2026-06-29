"""AI-backed value insights for meal details."""

import hashlib
import json
import logging
from typing import Any

from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.model.nutrition import Nutrition
from src.domain.services.meal_value_insight_contract import (
    IngredientValueInsight,
    MealValueInsights,
    ValueInsight,
    parse_ai_result,
    serialize_insights,
)
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.infra.services.ai.ai_model_manager import AIModelManager
from src.observability import log_event

INSIGHT_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
logger = logging.getLogger(__name__)


SUPPORTED_INSIGHT_LANGUAGES = {"en", "vi", "es", "fr", "de", "ja", "zh"}


class MealValueInsightService:
    """Build practical, non-medical meal insights using backend AI."""

    def __init__(
        self,
        ai_manager: AIModelManager | None = None,
        text_translation_service: DeepLTextTranslationService | None = None,
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
        cache_service: Any | None = None,
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
            cached_localized = await self._get_cached(cache_service, localized_cache_key)
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
            ai_manager = self._ai_manager or AIModelManager.get_instance()
            result = await ai_manager.generate(
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
            "ingredients": [
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
            ],
            "user_context": user_context,
        }

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
            "- category must be benefit, caution, or balance.\n"
            "- Ground claims in ingredients/macros/confidence. If uncertain, be generic or return empty arrays.\n"
            "- Keep total card copy near 280-320 characters or less.\n\n"
            "JSON shape:\n"
            '{"meal_bullets":[{"text":"...","category":"benefit"}],'
            '"ingredient_insights":[{"ingredient_name":"Egg","text":"...","category":"balance"}]}\n\n'
            f"Meal data:\n{json.dumps(summary, ensure_ascii=False)}"
        )

    def _cache_key(self, summary: dict[str, Any]) -> str:
        payload = json.dumps(summary, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return f"meal-value-insights:v1:{digest}"

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
        cache_service: Any | None,
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
        texts = [item.text for item in insights.meal_bullets]
        for item in insights.ingredient_insights:
            texts.extend([item.ingredient_name, item.text])

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
            meal_bullets.append(
                ValueInsight(text=translated[index], category=item.category)
            )
            index += 1

        ingredient_insights = []
        for item in insights.ingredient_insights:
            ingredient_insights.append(
                IngredientValueInsight(
                    ingredient_name=translated[index],
                    text=translated[index + 1],
                    category=item.category,
                )
            )
            index += 2

        localized = MealValueInsights(
            meal_bullets=meal_bullets,
            ingredient_insights=ingredient_insights,
        )
        return parse_ai_result(serialize_insights(localized))

    async def _get_cached(self, cache_service: Any | None, key: str):
        if cache_service is None:
            return None
        cached = await cache_service.get_json(key)
        return parse_ai_result(cached)

    async def _set_cached(
        self,
        cache_service: Any | None,
        key: str,
        insights: MealValueInsights,
    ) -> None:
        if cache_service is None:
            return
        await cache_service.set_json(
            key,
            serialize_insights(insights),
            INSIGHT_CACHE_TTL_SECONDS,
        )
