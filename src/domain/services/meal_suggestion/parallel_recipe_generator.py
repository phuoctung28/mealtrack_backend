"""
Parallel recipe generation for meal suggestions.
Implements 3-phase: name generation → parallel recipe generation → translation.
Per-recipe attempt logic lives in recipe_attempt_builder.py.
"""
import asyncio
import logging
import time
from typing import List, Optional, Tuple

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
from src.domain.services.meal_suggestion.recipe_attempt_builder import attempt_recipe_generation
from src.domain.services.meal_suggestion.translation_service import TranslationService

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en": "English", "vi": "Vietnamese", "fr": "French", "es": "Spanish",
    "de": "German", "it": "Italian", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "ru": "Russian", "pt": "Portuguese", "hi": "Hindi",
    "ar": "Arabic", "tr": "Turkish", "nl": "Dutch", "pl": "Polish",
    "sv": "Swedish", "da": "Danish", "fi": "Finnish", "no": "Norwegian",
    "cs": "Czech", "el": "Greek", "he": "Hebrew", "id": "Indonesian",
    "ms": "Malay", "th": "Thai",
}


def get_language_name(code: str) -> str:
    """Map language code to full English name for prompt instructions."""
    return LANGUAGE_NAMES.get(code.lower(), "English")


class ParallelRecipeGenerator:
    """
    3-phase parallel meal generation:
      Phase 1 — 4 diverse meal names (1 AI call, ~1-2s)
      Phase 2 — 4 recipes in parallel, take first 3 successes (~6-8s)
      Phase 3 — Translate to target language if non-English (~2-3s)
    """

    SUGGESTIONS_COUNT = 3
    MIN_ACCEPTABLE_RESULTS = 2
    PHASE1_TIMEOUT = 20

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        translation_service: TranslationService,
        macro_validator: MacroValidationService,
    ) -> None:
        self._generation = generation_service
        self._translation_service = translation_service
        self._macro_validator = macro_validator

    async def generate(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
    ) -> List[MealSuggestion]:
        """Run 3-phase generation. Raises RuntimeError if < MIN_ACCEPTABLE_RESULTS succeed."""
        start_time = time.time()
        target_lang = get_language_name(session.language)

        meal_names = await self._phase1_generate_names(session, exclude_meal_names, target_lang)
        phase1_elapsed = time.time() - start_time

        suggestions = await self._phase2_generate_recipes(session, meal_names, target_lang)
        phase2_elapsed = time.time() - start_time - phase1_elapsed

        phase3_elapsed = 0.0
        if session.language and session.language != "en":
            suggestions, phase3_elapsed = await self._phase3_translate(session, suggestions, target_lang)

        total_elapsed = time.time() - start_time
        logger.info(
            f"[PIPELINE-COMPLETE] session={session.id} | total_elapsed={total_elapsed:.2f}s | "
            f"phase1={phase1_elapsed:.2f}s | phase2={phase2_elapsed:.2f}s | "
            f"phase3={phase3_elapsed:.2f}s | language={session.language} | "
            f"returned={len(suggestions)} | meals={[s.meal_name for s in suggestions]}"
        )
        return suggestions

    async def _phase1_generate_names(
        self, session: SuggestionSession, exclude_meal_names: List[str], target_lang: str
    ) -> List[str]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_meal_names_prompt
        from src.domain.schemas.meal_generation_schemas import MealNamesResponse

        logger.info(
            f"[PHASE-1-START] session={session.id} | generating 4 names in {target_lang} | "
            f"excluding {len(exclude_meal_names)} previous meals"
        )
        names_system = (
            f"You are a creative chef. Generate 4 VERY DIFFERENT meal names with "
            f"diverse flavors and cooking styles. Output content in {target_lang}. "
            "IMPORTANT: Keep all JSON keys (like 'meal_names') in English."
        )
        try:
            names_raw = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generation.generate_meal_plan,
                    build_meal_names_prompt(session, exclude_meal_names),
                    names_system, "json", 1000, MealNamesResponse, "meal_names",
                ),
                timeout=self.PHASE1_TIMEOUT,
            )
            seen: set = set()
            meal_names = [
                n for n in names_raw.get("meal_names", [])
                if not (n.lower() in seen or seen.add(n.lower()))  # type: ignore[func-returns-value]
            ]
            if len(meal_names) < self.SUGGESTIONS_COUNT:
                raise RuntimeError("Could not generate enough unique meal names.")
            logger.info(f"[PHASE-1-COMPLETE] session={session.id} | names={meal_names}")
            return meal_names
        except Exception as e:
            logger.error(f"[PHASE-1-FAILED] session={session.id} | {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to generate meal names: {e}") from e

    async def _phase2_generate_recipes(
        self, session: SuggestionSession, meal_names: List[str], target_lang: str
    ) -> List[MealSuggestion]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_recipe_details_prompt

        logger.info(f"[PHASE-2-START] session={session.id} | recipes for {meal_names}")
        recipe_system = (
            "You are a professional chef and nutritionist. Return ONLY this exact JSON structure:\n"
            '{{"ingredients":[{{"name":"...","amount":0.0,"unit":"g"}}],'
            '"recipe_steps":[{{"step":1,"instruction":"...","duration_minutes":0}}],'
            '"prep_time_minutes":0,"calories":0,"protein":0.0,"carbs":0.0,"fat":0.0}}\n'
            "All ingredient amounts MUST be in GRAMS. Verify: calories=protein*4+carbs*4+fat*9.\n"
            f"Output string values in {target_lang}. JSON keys in English only."
        )
        prompts = [build_recipe_details_prompt(n, session) for n in meal_names]
        tasks = [
            asyncio.create_task(self._generate_with_retry(prompts[i], meal_names[i], i, recipe_system, session))
            for i in range(4)
        ]

        gen_start = time.time()
        successful: List[MealSuggestion] = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result is not None:
                    successful.append(result)
                    if len(successful) >= self.SUGGESTIONS_COUNT:
                        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
                        logger.info(f"[EARLY-STOP] Got 3 meals, cancelled {cancelled} tasks")
                        break
            except Exception as e:
                logger.warning(f"[RECIPE-ERROR] {type(e).__name__}: {e}")

        logger.info(
            f"[PHASE-2-COMPLETE] session={session.id} | "
            f"success={len(successful)}/4 | elapsed={time.time()-gen_start:.2f}s"
        )
        if len(successful) < self.MIN_ACCEPTABLE_RESULTS:
            if not successful:
                raise RuntimeError("Failed to generate any recipes from 4 attempts")
            raise RuntimeError(f"Insufficient recipes: {len(successful)}/{self.MIN_ACCEPTABLE_RESULTS} minimum")
        if len(successful) < self.SUGGESTIONS_COUNT:
            logger.warning(f"[PHASE-2-PARTIAL] session={session.id} | returning {len(successful)}/3 meals")
        return successful

    async def _generate_with_retry(
        self, prompt: str, meal_name: str, index: int, recipe_system: str, session: SuggestionSession
    ) -> Optional[MealSuggestion]:
        """Try primary model pool; retry on alternate pool if first attempt fails."""
        primary = "recipe_primary" if index % 2 == 0 else "recipe_secondary"
        result = await attempt_recipe_generation(
            self._generation, self._macro_validator, prompt, meal_name, index, primary, recipe_system, session
        )
        if result is not None:
            return result
        alternate = "recipe_secondary" if primary == "recipe_primary" else "recipe_primary"
        logger.info(f"[PHASE-2-RETRY] index={index} | {primary} → {alternate} | meal={meal_name}")
        return await attempt_recipe_generation(
            self._generation, self._macro_validator, prompt, meal_name, index, alternate, recipe_system, session,
            is_retry=True,
        )

    async def _phase3_translate(
        self, session: SuggestionSession, suggestions: List[MealSuggestion], target_lang: str
    ) -> Tuple[List[MealSuggestion], float]:
        """Translate to target language. Returns (suggestions, elapsed_seconds)."""
        start = time.time()
        logger.info(f"[PHASE-3-START] session={session.id} | translating {len(suggestions)} meals to {target_lang}")
        try:
            translated = await self._translation_service.translate_meal_suggestions_batch(
                suggestions, session.language
            )
            elapsed = time.time() - start
            logger.info(f"[PHASE-3-COMPLETE] session={session.id} | elapsed={elapsed:.2f}s | {len(translated)} meals")
            return translated, elapsed
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[PHASE-3-FAILED] session={session.id} | {type(e).__name__}: {e} | using English fallback")
            return suggestions, elapsed
