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
from src.domain.services.meal_suggestion.nutrition_lookup_service import NutritionLookupService
from src.domain.services.meal_suggestion.recipe_attempt_builder import attempt_recipe_generation

logger = logging.getLogger(__name__)

RECIPE_SYSTEM_PROMPT = (
    "You are a professional chef and nutritionist. Return ONLY this exact JSON structure:\n"
    '{{"ingredients":[{{"name":"...","amount":0.0,"unit":"g"}}],'
    '"recipe_steps":[{{"step":1,"instruction":"...","duration_minutes":0}}],'
    '"prep_time_minutes":0,"calories":0,"protein":0.0,"carbs":0.0,"fat":0.0}}\n'
    "All ingredient amounts MUST be in GRAMS. Verify: calories=protein*4+carbs*4+fat*9.\n"
    "Output string values in English. JSON keys in English only."
)

NAMES_TO_GENERATE = 4


class ParallelRecipeGenerator:
    """
    2-phase parallel meal generation:
      Phase 1 — 4 diverse meal names (1 AI call, ~1-2s)
      Phase 2 — 4 recipes in parallel, take first 3 successes (~6-8s)
    """

    DEFAULT_SUGGESTIONS_COUNT = 3
    MIN_ACCEPTABLE_RESULTS = 2
    PHASE1_TIMEOUT = 20
    DISCOVERY_TIMEOUT = 15

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        macro_validator: MacroValidationService,
        nutrition_lookup: NutritionLookupService,
    ) -> None:
        self._generation = generation_service
        self._macro_validator = macro_validator
        self._nutrition_lookup = nutrition_lookup

    async def generate(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
        suggestion_count: Optional[int] = None,
    ) -> List[MealSuggestion]:
        count = suggestion_count or self.DEFAULT_SUGGESTIONS_COUNT
        """Run 2-phase generation. Raises RuntimeError if < MIN_ACCEPTABLE_RESULTS succeed."""
        start_time = time.time()

        meal_names = await self._phase1_generate_names(
            session, exclude_meal_names, "English", count
        )
        phase1_elapsed = time.time() - start_time

        suggestions = await self._phase2_generate_recipes(
            session, meal_names, "English", count, preserve_order=False
        )
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
        meal_names = await self._phase1_generate_names(
            session, exclude_meal_names, "English", self.DEFAULT_SUGGESTIONS_COUNT
        )

        for idx, meal_name in enumerate(
            meal_names[: self.DEFAULT_SUGGESTIONS_COUNT]
        ):
            yield {
                "event": "meal_name",
                "data": {
                    "index": idx,
                    "meal_name": meal_name,
                },
            }

        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_recipe_details_prompt

        prompts = [build_recipe_details_prompt(name, session) for name in meal_names]
        tasks = [
            asyncio.create_task(
                self._generate_with_retry(prompts[i], meal_names[i], i, RECIPE_SYSTEM_PROMPT, session)
            )
            for i in range(len(meal_names))
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
                    if len(successful) >= self.DEFAULT_SUGGESTIONS_COUNT:
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        break
            except Exception as e:
                yield {
                    "event": "error",
                    "data": {"message": "Recipe generation failed"},
                }

        if len(successful) < self.MIN_ACCEPTABLE_RESULTS:
            if not successful:
                raise RuntimeError(f"Failed to generate any recipes from {len(meal_names)} attempts")
            raise RuntimeError(
                f"Insufficient recipes: {len(successful)}/{self.MIN_ACCEPTABLE_RESULTS} minimum"
            )

    async def generate_discovery(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
        count: int = 6,
    ) -> List[dict]:
        """Lightweight discovery: single AI call → list of {name, calories, P, C, F}.

        Returns list of dicts with validated macros. ~200 tokens total.
        """
        from src.domain.services.prompts.prompt_template_manager import PromptTemplateManager
        from src.domain.schemas.meal_generation_schemas import DiscoveryMealsResponse

        start = time.time()
        # Request extra for dedup headroom
        request_count = count + 2

        system = (
            f"You are a creative chef and nutritionist. Generate {request_count} VERY DIFFERENT meals. "
            "CRITICAL: ALL meal names MUST be in ENGLISH ONLY. Do NOT use Vietnamese, Japanese, or any "
            "non-English words in meal names. Translate ingredient names to English. Return valid JSON only."
        )
        prompt = PromptTemplateManager.build_discovery_prompt(
            meal_type=session.meal_type,
            target_calories=session.target_calories,
            count=request_count,
            ingredients=session.ingredients[:4] if session.ingredients else [],
            cuisine_region=getattr(session, "cuisine_region", None),
            exclude_meal_names=exclude_meal_names,
            protein_target=getattr(session, "protein_target", None),
            carbs_target=getattr(session, "carbs_target", None),
            fat_target=getattr(session, "fat_target", None),
        )

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generation.generate_meal_plan,
                    prompt, system, "json", 1000, DiscoveryMealsResponse, "meal_names",
                ),
                timeout=self.DISCOVERY_TIMEOUT,
            )
        except Exception as e:
            logger.error(f"[DISCOVERY-FAILED] session={session.id} | {type(e).__name__}: {e}")
            raise RuntimeError(f"Discovery generation failed: {e}") from e

        # Dedup + validate macros
        seen: set = set()
        results: list = []
        raw_meals = raw.get("meals", [])
        for meal in raw_meals:
            name = meal.get("name", "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())

            macros = self._macro_validator.validate_and_correct({
                "calories": meal.get("calories", 0),
                "protein": meal.get("protein", 0),
                "carbs": meal.get("carbs", 0),
                "fat": meal.get("fat", 0),
            })

            results.append({
                "name": name,
                "english_name": name,
                "calories": macros["calories"],
                "protein": macros["protein"],
                "carbs": macros["carbs"],
                "fat": macros["fat"],
            })

            if len(results) >= count:
                break

        elapsed = time.time() - start
        logger.info(
            f"[DISCOVERY-COMPLETE] session={session.id} | elapsed={elapsed:.2f}s | "
            f"meals={[r['name'] for r in results]}"
        )

        if not results:
            raise RuntimeError("Discovery returned no valid meals")

        return results

    async def _phase1_generate_names(
        self, session: SuggestionSession, exclude_meal_names: List[str], target_lang: str,
        suggestion_count: int = 3,
    ) -> List[str]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_meal_names_prompt
        from src.domain.schemas.meal_generation_schemas import MealNamesResponse

        # Request extra names for headroom (failures, dedup); retry once on shortage
        names_to_generate = suggestion_count + 4
        logger.info(
            f"[PHASE-1-START] session={session.id} | generating {names_to_generate} names in {target_lang} | "
            f"excluding {len(exclude_meal_names)} previous meals"
        )
        # Always generate names in English — Phase 3 translates to target language.
        # English names are preserved in MealSuggestion.english_name for image search.
        names_system = (
            f"You are a creative chef. Generate {names_to_generate} VERY DIFFERENT meal names with "
            f"diverse flavors and cooking styles. Each name must be unique. "
            "Output meal names in ENGLISH. Keep all JSON keys in English."
        )
        seen: set = set()
        meal_names: list = []
        max_attempts = 2
        try:
            for attempt in range(1, max_attempts + 1):
                names_raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generation.generate_meal_plan,
                        build_meal_names_prompt(session, exclude_meal_names, names_to_generate),
                        names_system, "json", 1000, MealNamesResponse, "meal_names",
                    ),
                    timeout=self.PHASE1_TIMEOUT,
                )
                for n in names_raw.get("meal_names", []):
                    if n.lower() not in seen:
                        seen.add(n.lower())
                        meal_names.append(n)
                if len(meal_names) >= suggestion_count:
                    break
                logger.warning(
                    f"[PHASE-1-RETRY] session={session.id} | attempt={attempt} | "
                    f"got {len(meal_names)} unique names, need {suggestion_count}"
                )
            if len(meal_names) < suggestion_count:
                raise RuntimeError(
                    f"Could not generate enough unique meal names "
                    f"(got {len(meal_names)}, need {suggestion_count})."
                )
            logger.info(f"[PHASE-1-COMPLETE] session={session.id} | names={meal_names}")
            return meal_names
        except Exception as e:
            logger.error(f"[PHASE-1-FAILED] session={session.id} | {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to generate meal names: {e}") from e

    async def _phase2_generate_recipes(
        self, session: SuggestionSession, meal_names: List[str], target_lang: str,
        suggestion_count: int = 3,
        min_acceptable_override: int = 0,
        preserve_order: bool = True,
    ) -> List[MealSuggestion]:
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import build_recipe_details_prompt

        total_attempts = len(meal_names)
        min_acceptable = min_acceptable_override or max(suggestion_count - 1, self.MIN_ACCEPTABLE_RESULTS)
        logger.info(f"[PHASE-2-START] session={session.id} | recipes for {meal_names} | preserve_order={preserve_order}")
        recipe_system = (
            "You are a professional chef. Return ONLY this exact JSON structure:\n"
            '{{"ingredients":[{{"name":"...","amount":0.0,"unit":"g"}}],'
            '"recipe_steps":[{{"step":1,"instruction":"...","duration_minutes":0}}],'
            '"prep_time_minutes":0}}\n'
            "All ingredient amounts MUST be in GRAMS.\n"
            "CRITICAL: ALL text (ingredient names, instructions) MUST be in ENGLISH ONLY. "
            "Do NOT include Vietnamese, Japanese, or any non-English text (no 'gà', 'cơm', 'trứng' — "
            "use 'chicken', 'rice', 'egg'). No parenthetical translations. JSON keys in English only."
        )
        prompts = [build_recipe_details_prompt(n, session) for n in meal_names]
        tasks = [
            asyncio.create_task(self._generate_with_retry(prompts[i], meal_names[i], i, recipe_system, session))
            for i in range(total_attempts)
        ]

        gen_start = time.time()
        successful: List[MealSuggestion] = []

        if preserve_order:
            # gather preserves submission order — required for /recipes endpoint where mobile
            # pairs results to selected meal names by index position.
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"[RECIPE-ERROR] {type(result).__name__}: {result}")
                elif result is not None:
                    successful.append(result)
        else:
            # as_completed yields in completion-time order, enabling early-stop once
            # suggestion_count successes arrive. Used by the discovery flow which spawns
            # total_attempts > suggestion_count tasks for headroom.
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    if result is not None:
                        successful.append(result)
                        if len(successful) >= suggestion_count:
                            cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
                            logger.info(f"[EARLY-STOP] Got {suggestion_count} meals, cancelled {cancelled} tasks")
                            break
                except Exception as e:
                    logger.warning(f"[RECIPE-ERROR] {type(e).__name__}: {e}")

        logger.info(
            f"[PHASE-2-COMPLETE] session={session.id} | "
            f"success={len(successful)}/{total_attempts} | elapsed={time.time()-gen_start:.2f}s"
        )
        if len(successful) < min_acceptable:
            if not successful:
                raise RuntimeError(f"Failed to generate any recipes from {total_attempts} attempts")
            raise RuntimeError(f"Insufficient recipes: {len(successful)}/{min_acceptable} minimum")
        if len(successful) < suggestion_count:
            logger.warning(f"[PHASE-2-PARTIAL] session={session.id} | returning {len(successful)}/{suggestion_count} meals")
        return successful

    async def _generate_with_retry(
        self, prompt: str, meal_name: str, index: int, recipe_system: str, session: SuggestionSession
    ) -> Optional[MealSuggestion]:
        """Try primary model pool; retry on alternate pool if first attempt fails."""
        primary = "recipe_primary" if index % 2 == 0 else "recipe_secondary"
        result = await attempt_recipe_generation(
            self._generation, self._macro_validator, self._nutrition_lookup,
            prompt, meal_name, index, primary, recipe_system, session,
        )
        if result is not None:
            return result
        alternate = "recipe_secondary" if primary == "recipe_primary" else "recipe_primary"
        logger.info(f"[PHASE-2-RETRY] index={index} | {primary} → {alternate} | meal={meal_name}")
        return await attempt_recipe_generation(
            self._generation, self._macro_validator, self._nutrition_lookup,
            prompt, meal_name, index, alternate, recipe_system, session,
            is_retry=True,
        )
