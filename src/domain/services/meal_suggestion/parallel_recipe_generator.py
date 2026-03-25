"""
Parallel recipe generation for meal suggestions.
Implements 2-phase: name generation → parallel recipe generation.
Per-recipe attempt logic lives in recipe_attempt_builder.py.
"""
import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
from src.domain.services.meal_suggestion.recipe_attempt_builder import attempt_recipe_generation

logger = logging.getLogger(__name__)


class ParallelRecipeGenerator:
    """
    2-phase parallel meal generation:
      Phase 1 — 4 diverse meal names (1 AI call, ~1-2s)
      Phase 2 — 4 recipes in parallel, take first 3 successes (~6-8s)
    """

    SUGGESTIONS_COUNT = 3
    MIN_ACCEPTABLE_RESULTS = 2
    PHASE1_TIMEOUT = 20

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        macro_validator: MacroValidationService,
    ) -> None:
        self._generation = generation_service
        self._macro_validator = macro_validator

    async def generate(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
    ) -> List[MealSuggestion]:
        """Run 2-phase generation. Raises RuntimeError if < MIN_ACCEPTABLE_RESULTS succeed."""
        start_time = time.time()

        meal_names = await self._phase1_generate_names(session, exclude_meal_names)
        phase1_elapsed = time.time() - start_time

        suggestions = await self._phase2_generate_recipes(session, meal_names)
        phase2_elapsed = time.time() - start_time - phase1_elapsed

        total_elapsed = time.time() - start_time
        logger.info(
            f"[PIPELINE-COMPLETE] session={session.id} | total_elapsed={total_elapsed:.2f}s | "
            f"phase1={phase1_elapsed:.2f}s | phase2={phase2_elapsed:.2f}s | "
            f"language={session.language} | "
            f"returned={len(suggestions)} | meals={[s.meal_name for s in suggestions]}"
        )
        return suggestions

    async def generate_stream(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream generation events for progressive UI updates."""
        meal_names = await self._phase1_generate_names(session, exclude_meal_names)

        for idx, meal_name in enumerate(meal_names[: self.SUGGESTIONS_COUNT]):
            yield {
                "event": "meal_name",
                "data": {
                    "index": idx,
                    "meal_name": meal_name,
                },
            }

        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_recipe_details_prompt

        recipe_system = (
            "You are a professional chef and nutritionist. Return ONLY this exact JSON structure:\n"
            '{{"ingredients":[{{"name":"...","amount":0.0,"unit":"g"}}],'
            '"recipe_steps":[{{"step":1,"instruction":"...","duration_minutes":0}}],'
            '"prep_time_minutes":0,"calories":0,"protein":0.0,"carbs":0.0,"fat":0.0}}\n'
            "All ingredient amounts MUST be in GRAMS. Verify: calories=protein*4+carbs*4+fat*9.\n"
            "Output string values in English. JSON keys in English only."
        )
        prompts = [build_recipe_details_prompt(name, session) for name in meal_names]
        tasks = [
            asyncio.create_task(
                self._generate_with_retry(prompts[i], meal_names[i], i, recipe_system, session)
            )
            for i in range(4)
        ]

        successful: List[MealSuggestion] = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result is not None:
                    successful.append(result)
                    yield {
                        "event": "meal_detail",
                        "data": {
                            "index": len(successful) - 1,
                            "suggestion": result,
                        },
                    }
                    if len(successful) >= self.SUGGESTIONS_COUNT:
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        break
            except Exception as e:
                yield {
                    "event": "error",
                    "data": {"message": f"Recipe generation failed: {str(e)}"},
                }

        if len(successful) < self.MIN_ACCEPTABLE_RESULTS:
            if not successful:
                raise RuntimeError("Failed to generate any recipes from 4 attempts")
            raise RuntimeError(
                f"Insufficient recipes: {len(successful)}/{self.MIN_ACCEPTABLE_RESULTS} minimum"
            )

    async def _phase1_generate_names(
        self, session: SuggestionSession, exclude_meal_names: List[str]
    ) -> List[str]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_meal_names_prompt
        from src.domain.schemas.meal_generation_schemas import MealNamesResponse

        logger.info(
            f"[PHASE-1-START] session={session.id} | generating 4 names in English | "
            f"excluding {len(exclude_meal_names)} previous meals"
        )
        names_system = (
            "You are a creative chef. Generate 4 VERY DIFFERENT meal names with "
            "diverse flavors and cooking styles. Output content in English. "
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
        self, session: SuggestionSession, meal_names: List[str]
    ) -> List[MealSuggestion]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_recipe_details_prompt

        logger.info(f"[PHASE-2-START] session={session.id} | recipes for {meal_names}")
        recipe_system = (
            "You are a professional chef and nutritionist. Return ONLY this exact JSON structure:\n"
            '{{"ingredients":[{{"name":"...","amount":0.0,"unit":"g"}}],'
            '"recipe_steps":[{{"step":1,"instruction":"...","duration_minutes":0}}],'
            '"prep_time_minutes":0,"calories":0,"protein":0.0,"carbs":0.0,"fat":0.0}}\n'
            "All ingredient amounts MUST be in GRAMS. Verify: calories=protein*4+carbs*4+fat*9.\n"
            "Output string values in English. JSON keys in English only."
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

