"""Angle-tolerant meal scan cache via AI visual identity + scene signature.

OpenAI prompt caching only reuses system-prompt prefixes for cost. It does not
return the same meal for different photos. This service asks a cheap vision
pass for an angle-invariant identity, compares scene color signatures, and
reuses the prior READY meal when both signals agree.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_scan_visual_identity import (
    MealScanVisualIdentity,
    ParsedVisualIdentity,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import FoodVisualIdentityStrategy
from src.domain.utils.scene_signature import (
    build_scene_signature,
    ingredient_jaccard,
    scene_cosine_similarity,
)
from src.domain.utils.timezone_utils import utc_now
from src.observability import increment_metric

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def scan_source_for_mode(scan_mode: str) -> str:
    return "food_label" if scan_mode == "food_label" else "scanner"


def _slug(value: str | None, *, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    cleaned = _SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return cleaned[:128] or fallback


def build_identity_key(
    *,
    dish_slug: str,
    ingredients: list[str] | tuple[str, ...],
    container: str | None,
    background: str | None,
) -> str:
    ingredient_part = ",".join(sorted({_slug(i) for i in ingredients if i}))
    return "|".join(
        (
            _slug(dish_slug),
            ingredient_part,
            _slug(container, fallback=""),
            _slug(background, fallback=""),
        )
    )


def parse_visual_identity(
    vision_result: dict[str, Any] | Any,
) -> ParsedVisualIdentity | None:
    if not isinstance(vision_result, dict):
        return None
    structured = vision_result.get("structured_data")
    payload = structured if isinstance(structured, dict) else vision_result
    if not isinstance(payload, dict):
        return None

    is_food = payload.get("is_food", True)
    if is_food is False:
        return ParsedVisualIdentity(
            dish_slug="not_food",
            ingredients=(),
            container=None,
            background=None,
            identity_key="not_food",
            is_food=False,
            confidence=float(payload.get("confidence") or 0.0),
        )

    dish_slug = _slug(str(payload.get("dish_slug") or payload.get("dish_name") or ""))
    raw_ingredients = payload.get("ingredients") or []
    if not isinstance(raw_ingredients, list):
        raw_ingredients = []
    ingredients = tuple(
        sorted({_slug(str(item)) for item in raw_ingredients if str(item).strip()})
    )
    container = payload.get("container")
    background = payload.get("background")
    container_slug = _slug(str(container), fallback="") if container else None
    background_slug = _slug(str(background), fallback="") if background else None
    if container_slug == "":
        container_slug = None
    if background_slug == "":
        background_slug = None
    identity_key = build_identity_key(
        dish_slug=dish_slug,
        ingredients=ingredients,
        container=container_slug,
        background=background_slug,
    )
    return ParsedVisualIdentity(
        dish_slug=dish_slug,
        ingredients=ingredients,
        container=container_slug,
        background=background_slug,
        identity_key=identity_key,
        is_food=True,
        confidence=float(payload.get("confidence") or 0.0),
    )


def score_visual_match(
    *,
    parsed: ParsedVisualIdentity,
    candidate: MealScanVisualIdentity,
    scene_signature: list[float],
) -> float:
    if parsed.dish_slug != candidate.dish_slug:
        return 0.0
    scene = scene_cosine_similarity(scene_signature, candidate.scene_signature)
    ingredients = ingredient_jaccard(parsed.ingredients, candidate.ingredients)
    container = (
        1.0
        if parsed.container
        and candidate.container
        and parsed.container == candidate.container
        else 0.5
        if not parsed.container or not candidate.container
        else 0.0
    )
    background = (
        1.0
        if parsed.background
        and candidate.background
        and parsed.background == candidate.background
        else 0.5
        if not parsed.background or not candidate.background
        else 0.0
    )
    # Scene + ingredients dominate; container/background break ties.
    return (
        (0.45 * scene) + (0.35 * ingredients) + (0.10 * container) + (0.10 * background)
    )


def mark_scan_cache_hit(meal: Meal) -> Meal:
    meal._meal_scan_cache_hit = True  # type: ignore[attr-defined]
    meal._meal_value_insight_scheduled = True  # type: ignore[attr-defined]
    return meal


class MealScanVisualCacheService:
    """Resolve prior meals for re-scans of the same food at new angles."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        vision_service: VisionAIServicePort | None = None,
        *,
        enabled: bool = False,
        match_threshold: float = 0.82,
        min_identity_confidence: float = 0.55,
    ):
        self._uow = uow
        self._vision_service = vision_service
        self._enabled = enabled
        self._match_threshold = match_threshold
        self._min_identity_confidence = min_identity_confidence
        self._last_parsed: ParsedVisualIdentity | None = None
        self._last_scene_signature: list[float] | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled and self._vision_service is not None

    async def try_resolve(
        self,
        *,
        user_id: str,
        image_bytes: bytes,
        source: str,
    ) -> Meal | None:
        if not self.enabled:
            return None
        try:
            return await self._try_resolve_inner(
                user_id=user_id,
                image_bytes=image_bytes,
                source=source,
            )
        except Exception as exc:
            logger.warning("[MEAL-VISUAL-CACHE] resolve failed: %s", exc)
            return None

    async def _try_resolve_inner(
        self,
        *,
        user_id: str,
        image_bytes: bytes,
        source: str,
    ) -> Meal | None:
        if source == "food_label":
            return None

        async with self._uow as uow:
            repo = getattr(uow, "meal_scan_visual_identities", None)
            if repo is None:
                return None
            prior_count = await repo.count_for_user_source(
                user_id=user_id, source=source
            )
        if not isinstance(prior_count, int) or prior_count <= 0:
            return None

        try:
            scene_signature = build_scene_signature(image_bytes)
        except Exception as exc:
            logger.warning("[MEAL-VISUAL-CACHE] scene signature failed: %s", exc)
            return None

        assert self._vision_service is not None
        try:
            vision_result = await self._vision_service.analyze_with_strategy(  # type: ignore[attr-defined]
                image_bytes,
                FoodVisualIdentityStrategy(),
            )
        except Exception as exc:
            logger.warning("[MEAL-VISUAL-CACHE] identity vision failed: %s", exc)
            increment_metric(
                "meal_scan.visual_cache.identity_failure",
                attributes={"component": "meal_scan_visual_cache"},
            )
            return None

        parsed = parse_visual_identity(vision_result)
        if parsed is None or not parsed.is_food:
            return None
        if parsed.confidence < self._min_identity_confidence:
            return None

        async with self._uow as uow:
            repo = uow.meal_scan_visual_identities
            exact = await repo.find_by_identity_key(
                user_id=user_id,
                identity_key=parsed.identity_key,
                source=source,
            )
            candidates = exact or await repo.list_by_user_source_dish(
                user_id=user_id,
                source=source,
                dish_slug=parsed.dish_slug,
            )

        best: MealScanVisualIdentity | None = None
        best_score = 0.0
        for candidate in candidates:
            if not isinstance(candidate, MealScanVisualIdentity):
                continue
            score = score_visual_match(
                parsed=parsed,
                candidate=candidate,
                scene_signature=scene_signature,
            )
            if score > best_score:
                best_score = score
                best = candidate

        self._last_parsed = parsed
        self._last_scene_signature = scene_signature

        if best is None or best_score < self._match_threshold:
            increment_metric(
                "meal_scan.visual_cache.miss",
                attributes={"component": "meal_scan_visual_cache"},
            )
            return None

        async with self._uow as uow:
            meal = await uow.meals.find_by_id(best.meal_id)
        if not isinstance(meal, Meal):
            return None
        if meal.user_id != user_id:
            return None
        if meal.status != MealStatus.READY or meal.nutrition is None:
            return None

        increment_metric(
            "meal_scan.visual_cache.hit",
            attributes={"component": "meal_scan_visual_cache"},
        )
        logger.info(
            "[MEAL-VISUAL-CACHE] hit user=%s meal=%s score=%.3f identity=%s",
            user_id,
            meal.meal_id,
            best_score,
            parsed.identity_key,
        )
        return mark_scan_cache_hit(meal)

    async def remember(
        self,
        *,
        user_id: str,
        meal: Meal,
        image_bytes: bytes,
        source: str,
        vision_identity: ParsedVisualIdentity | None = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            await self._remember_inner(
                user_id=user_id,
                meal=meal,
                image_bytes=image_bytes,
                source=source,
                vision_identity=vision_identity,
            )
        except Exception as exc:
            logger.warning("[MEAL-VISUAL-CACHE] remember failed: %s", exc)

    async def _remember_inner(
        self,
        *,
        user_id: str,
        meal: Meal,
        image_bytes: bytes,
        source: str,
        vision_identity: ParsedVisualIdentity | None = None,
    ) -> None:
        if source == "food_label":
            return
        if meal.status != MealStatus.READY or meal.nutrition is None:
            return

        parsed = vision_identity or self._last_parsed
        scene_signature = self._last_scene_signature
        self._last_parsed = None
        self._last_scene_signature = None

        if parsed is None:
            dish_slug = _slug(meal.dish_name)
            ingredients: list[str] = []
            if meal.nutrition and meal.nutrition.food_items:
                ingredients = [
                    _slug(item.name)
                    for item in meal.nutrition.food_items
                    if getattr(item, "name", None)
                ]
            parsed = ParsedVisualIdentity(
                dish_slug=dish_slug,
                ingredients=tuple(sorted(set(ingredients))),
                container=None,
                background=None,
                identity_key=build_identity_key(
                    dish_slug=dish_slug,
                    ingredients=ingredients,
                    container=None,
                    background=None,
                ),
                is_food=True,
                confidence=0.5,
            )
        if not parsed.is_food or parsed.dish_slug in {"", "unknown", "not_food"}:
            return

        if scene_signature is None:
            try:
                scene_signature = build_scene_signature(image_bytes)
            except Exception as exc:
                logger.warning("[MEAL-VISUAL-CACHE] remember scene failed: %s", exc)
                return

        identity = MealScanVisualIdentity(
            id=str(uuid4()),
            user_id=user_id,
            meal_id=meal.meal_id,
            source=source,
            dish_slug=parsed.dish_slug,
            ingredients=parsed.ingredients,
            container=parsed.container,
            background=parsed.background,
            identity_key=parsed.identity_key,
            scene_signature=tuple(scene_signature),
            created_at=utc_now(),
        )
        async with self._uow as uow:
            repo = getattr(uow, "meal_scan_visual_identities", None)
            if repo is None:
                return
            await repo.save(identity)
            await uow.commit()
        logger.info(
            "[MEAL-VISUAL-CACHE] remembered user=%s meal=%s identity=%s",
            user_id,
            meal.meal_id,
            parsed.identity_key,
        )
