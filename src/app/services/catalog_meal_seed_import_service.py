"""Additive importer for curated meal recommendation catalog seeds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
)
from src.domain.services.meal_recommendation.ingredient_quantity_conversion_service import (
    IngredientQuantityConversionError,
    IngredientQuantityConversionService,
    ResolvedIngredientQuantity,
)
from src.domain.services.meal_suggestion.ingredient_name_normalizer import (
    normalize_food_name,
)
from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.meal_recommendation import (
    MealCatalogIngredientORM,
    MealCatalogORM,
)
from src.infra.repositories.food_reference_projection import (
    food_reference_model_to_nutrition_projection,
)


@dataclass(frozen=True)
class _FoodReferenceSearchRow:
    """Lightweight row used for ingredient search and scoring."""

    food_reference_id: int
    name: str
    name_normalized: str | None
    source: str
    is_verified: bool
    protein_100g: float | None
    carbs_100g: float | None
    fat_100g: float | None
    fiber_100g: float
    sugar_100g: float
    density_g_ml: float | None


@dataclass(frozen=True)
class CatalogSeedResolutionCandidate:
    """Candidate food-reference match for one unresolved ingredient."""

    food_reference_id: int
    name: str
    name_normalized: str | None
    source: str
    is_verified: bool
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "food_reference_id": self.food_reference_id,
            "name": self.name,
            "name_normalized": self.name_normalized,
            "source": self.source,
            "is_verified": self.is_verified,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class CatalogSeedResolutionIssue:
    """Ingredient resolution issue with ranked candidates."""

    recipe_index: int
    recipe_key: str
    ingredient_index: int
    ingredient_name: str
    normalized_name: str
    reason: str
    candidates: tuple[CatalogSeedResolutionCandidate, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_index": self.recipe_index,
            "recipe_key": self.recipe_key,
            "ingredient_index": self.ingredient_index,
            "ingredient_name": self.ingredient_name,
            "normalized_name": self.normalized_name,
            "reason": self.reason,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class CatalogSeedImportSummary:
    """Import outcome for CLI reporting and tests."""

    inserted: int = 0
    skipped_existing: int = 0
    dry_run: bool = False
    errors: tuple[str, ...] = field(default_factory=tuple)
    resolution_issues: tuple[CatalogSeedResolutionIssue, ...] = field(
        default_factory=tuple
    )

    @property
    def is_successful(self) -> bool:
        return not self.errors

    def resolution_report(self) -> dict[str, Any]:
        return {
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "dry_run": self.dry_run,
            "errors": list(self.errors),
            "issues": [issue.to_dict() for issue in self.resolution_issues],
        }


class CatalogSeedImportError(ValueError):
    """Raised when a seed manifest cannot be imported safely."""


class CatalogSeedResolutionError(CatalogSeedImportError):
    """Raised when an ingredient needs manual resolution."""

    def __init__(self, issue: CatalogSeedResolutionIssue) -> None:
        self.issue = issue
        candidate_text = ", ".join(
            f"{item.food_reference_id}:{item.name}:{item.score:.2f}"
            for item in issue.candidates[:5]
        )
        suffix = f"; candidates: {candidate_text}" if candidate_text else ""
        super().__init__(
            f"recipes[{issue.recipe_index}].ingredients[{issue.ingredient_index}] "
            f"{issue.reason}: '{issue.ingredient_name}' "
            f"normalized='{issue.normalized_name}'{suffix}"
        )


class CatalogMealSeedImporter:
    """Import catalog meals additively with exact duplicate protection."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        dry_run: bool = False,
        approved_mappings: dict[str, int] | None = None,
        auto_resolve_threshold: float | None = 0.92,
        resolve_all_best_effort: bool = False,
        converter: IngredientQuantityConversionService | None = None,
    ) -> None:
        self._session = session
        self._dry_run = dry_run
        self._approved_mappings = {
            normalize_food_name(key): int(value)
            for key, value in (approved_mappings or {}).items()
        }
        self._auto_resolve_threshold = auto_resolve_threshold
        self._resolve_all_best_effort = resolve_all_best_effort
        self._converter = converter or IngredientQuantityConversionService(
            allow_unverified=resolve_all_best_effort,
            allow_unapproved_sources=resolve_all_best_effort,
            allow_implausible_macros=resolve_all_best_effort,
            allow_common_unit_fallbacks=resolve_all_best_effort,
        )
        self._candidate_rows: list[_FoodReferenceSearchRow] | None = None

    async def import_manifest(self, manifest: dict[str, Any]) -> CatalogSeedImportSummary:
        inserted = 0
        skipped = 0
        errors: list[str] = []
        resolution_issues: list[CatalogSeedResolutionIssue] = []
        for index, recipe in enumerate(manifest.get("recipes", [])):
            try:
                status = await self._import_recipe(recipe, index)
            except CatalogSeedResolutionError as exc:
                errors.append(str(exc))
                resolution_issues.append(exc.issue)
                continue
            except CatalogSeedImportError as exc:
                errors.append(str(exc))
                continue
            if status == "inserted":
                inserted += 1
            else:
                skipped += 1
        return CatalogSeedImportSummary(
            inserted=inserted,
            skipped_existing=skipped,
            dry_run=self._dry_run,
            errors=tuple(errors),
            resolution_issues=tuple(resolution_issues),
        )

    async def _import_recipe(self, recipe: dict[str, Any], index: int) -> str:
        catalog_key = str(recipe["recipe_key"]).strip()
        resolved_ingredients = await self._resolve_ingredients(recipe, index)
        content_hash = _content_hash(recipe, resolved_ingredients)
        existing = await self._find_existing(catalog_key, content_hash)
        if existing is not None:
            if existing.catalog_key == catalog_key and existing.content_hash != content_hash:
                raise CatalogSeedImportError(
                    f"recipes[{index}] catalog_key already exists with different content: "
                    f"{catalog_key}"
                )
            return "skipped"
        if self._dry_run:
            return "inserted"

        row = MealCatalogORM(
            catalog_key=catalog_key,
            content_hash=content_hash,
            name=str(recipe["name"]).strip(),
            cuisine=str(recipe["cuisine"]).strip(),
            description=_optional_string(recipe.get("description")),
            image_url=_optional_string(recipe.get("image_url")),
            breakfast_eligible="breakfast" in recipe["meal_types"],
            lunch_eligible="lunch" in recipe["meal_types"],
            dinner_eligible="dinner" in recipe["meal_types"],
            snack_eligible="snack" in recipe["meal_types"],
            is_active=True,
        )
        row.ingredients = [
            MealCatalogIngredientORM(
                food_reference_id=item.food_reference_id,
                display_name=item.display_name,
                quantity=item.quantity,
                unit=item.unit,
            )
            for item in resolved_ingredients
        ]
        self._session.add(row)
        await self._session.flush()
        return "inserted"

    async def _resolve_ingredients(
        self,
        recipe: dict[str, Any],
        recipe_index: int,
    ) -> list[ResolvedIngredientQuantity]:
        resolved: list[ResolvedIngredientQuantity] = []
        for ingredient_index, ingredient in enumerate(recipe.get("ingredients", [])):
            reference = await self._resolve_food_reference(
                ingredient,
                recipe_key=str(recipe["recipe_key"]).strip(),
                recipe_index=recipe_index,
                ingredient_index=ingredient_index,
            )
            try:
                resolved.append(
                    self._converter.resolve(
                        reference=reference,
                        quantity=float(ingredient["quantity"]),
                        unit=str(ingredient["unit"]).strip(),
                        display_name=str(ingredient["name"]).strip(),
                    )
                )
            except IngredientQuantityConversionError as exc:
                raise CatalogSeedImportError(
                    f"recipes[{recipe_index}].ingredients[{ingredient_index}] "
                    f"{exc.code}: {exc}"
                ) from exc
        return resolved

    async def _resolve_food_reference(
        self,
        ingredient: dict[str, Any],
        recipe_key: str,
        recipe_index: int,
        ingredient_index: int,
    ) -> FoodReferenceNutritionProjection:
        food_reference_id = ingredient.get("food_reference_id")
        if food_reference_id is not None:
            reference = await self._get_reference_by_id(int(food_reference_id))
            if reference is None:
                raise CatalogSeedImportError(
                    f"recipes[{recipe_index}].ingredients[{ingredient_index}] "
                    f"food_reference_id not found: {food_reference_id}"
                )
            return reference

        name = str(ingredient["name"]).strip()
        normalized = normalize_food_name(name)
        mapped_id = self._approved_mappings.get(normalized)
        if mapped_id is not None:
            reference = await self._get_reference_by_id(mapped_id)
            if reference is None:
                raise CatalogSeedImportError(
                    f"recipes[{recipe_index}].ingredients[{ingredient_index}] "
                    f"mapped food_reference_id not found: {mapped_id}"
                )
            return reference

        matches = await self._find_reference_candidates_by_normalized_name(normalized)
        verified_matches = [item for item in matches if item.is_verified]
        if self._resolve_all_best_effort and matches:
            reference = await self._get_reference_by_id(matches[0].food_reference_id)
            if reference is not None:
                return reference
        if len(verified_matches) == 1:
            reference = await self._get_reference_by_id(verified_matches[0].food_reference_id)
            if reference is not None:
                return reference
        if len(verified_matches) > 1:
            self._raise_resolution_issue(
                recipe_key,
                recipe_index,
                ingredient_index,
                name,
                normalized,
                "ambiguous_exact_match",
                tuple(verified_matches[:5]),
            )
        if len(matches) == 1:
            self._raise_resolution_issue(
                recipe_key,
                recipe_index,
                ingredient_index,
                name,
                normalized,
                "exact_match_not_verified",
                (matches[0],),
            )

        candidates = await self._ranked_candidates(normalized)
        accepted = _auto_resolved_candidate(
            candidates,
            self._auto_resolve_threshold,
            allow_unverified=self._resolve_all_best_effort,
        )
        if accepted is not None:
            reference = await self._get_reference_by_id(accepted.food_reference_id)
            if reference is not None:
                return reference
        self._raise_resolution_issue(
            recipe_key,
            recipe_index,
            ingredient_index,
            name,
            normalized,
            "needs_review",
            tuple(candidates[:5]),
        )

    async def _find_existing(
        self,
        catalog_key: str,
        content_hash: str,
    ) -> MealCatalogORM | None:
        result = await self._session.execute(
            select(MealCatalogORM).where(
                or_(
                    MealCatalogORM.catalog_key == catalog_key,
                    MealCatalogORM.content_hash == content_hash,
                )
            )
        )
        return result.scalars().first()

    async def _get_reference_by_id(
        self,
        food_reference_id: int,
    ) -> FoodReferenceNutritionProjection | None:
        for row in await self._all_candidate_rows():
            if row.food_reference_id == food_reference_id:
                return _projection_from_search_row(row)
        result = await self._session.execute(
            select(FoodReferenceModel)
            .where(FoodReferenceModel.id == food_reference_id)
            .options(
                selectinload(FoodReferenceModel.serving_size_rows),
                selectinload(FoodReferenceModel.nutrient_rows),
            )
        )
        row = result.scalars().first()
        return food_reference_model_to_nutrition_projection(row) if row else None

    async def _find_reference_candidates_by_normalized_name(
        self,
        name_normalized: str,
    ) -> list[CatalogSeedResolutionCandidate]:
        result = await self._session.execute(
            select(
                FoodReferenceModel.id,
                FoodReferenceModel.name,
                FoodReferenceModel.name_normalized,
                FoodReferenceModel.source,
                FoodReferenceModel.is_verified,
                FoodReferenceModel.protein_100g,
                FoodReferenceModel.carbs_100g,
                FoodReferenceModel.fat_100g,
                FoodReferenceModel.fiber_100g,
                FoodReferenceModel.sugar_100g,
                FoodReferenceModel.density,
            )
            .where(FoodReferenceModel.name_normalized == name_normalized)
            .order_by(FoodReferenceModel.is_verified.desc(), FoodReferenceModel.id.asc())
        )
        return [
            _candidate_from_search_row(
                _FoodReferenceSearchRow(
                    food_reference_id=int(row.id),
                    name=str(row.name),
                    name_normalized=row.name_normalized,
                    source=str(row.source),
                    is_verified=bool(row.is_verified),
                    protein_100g=row.protein_100g,
                    carbs_100g=row.carbs_100g,
                    fat_100g=row.fat_100g,
                    fiber_100g=row.fiber_100g or 0.0,
                    sugar_100g=row.sugar_100g or 0.0,
                    density_g_ml=row.density,
                ),
                1.0,
            )
            for row in result.all()
        ]

    async def _ranked_candidates(
        self,
        normalized_name: str,
    ) -> list[CatalogSeedResolutionCandidate]:
        rows = await self._all_candidate_rows()
        candidates = [
            _candidate_from_search_row(row, _candidate_score(normalized_name, row))
            for row in rows
        ]
        candidates = [candidate for candidate in candidates if candidate.score > 0.25]
        return sorted(
            candidates,
            key=lambda item: (-item.score, not item.is_verified, item.food_reference_id),
        )[:20]

    async def _all_candidate_rows(self) -> list[_FoodReferenceSearchRow]:
        if self._candidate_rows is not None:
            return self._candidate_rows
        result = await self._session.execute(
            select(
                FoodReferenceModel.id,
                FoodReferenceModel.name,
                FoodReferenceModel.name_normalized,
                FoodReferenceModel.source,
                FoodReferenceModel.is_verified,
                FoodReferenceModel.protein_100g,
                FoodReferenceModel.carbs_100g,
                FoodReferenceModel.fat_100g,
                FoodReferenceModel.fiber_100g,
                FoodReferenceModel.sugar_100g,
                FoodReferenceModel.density,
            ).order_by(
                FoodReferenceModel.is_verified.desc(),
                FoodReferenceModel.id.asc(),
            )
        )
        self._candidate_rows = [
            _FoodReferenceSearchRow(
                food_reference_id=int(row.id),
                name=str(row.name),
                name_normalized=row.name_normalized,
                source=str(row.source),
                is_verified=bool(row.is_verified),
                protein_100g=row.protein_100g,
                carbs_100g=row.carbs_100g,
                fat_100g=row.fat_100g,
                fiber_100g=row.fiber_100g or 0.0,
                sugar_100g=row.sugar_100g or 0.0,
                density_g_ml=row.density,
            )
            for row in result.all()
        ]
        return self._candidate_rows

    def _raise_resolution_issue(
        self,
        recipe_key: str,
        recipe_index: int,
        ingredient_index: int,
        ingredient_name: str,
        normalized_name: str,
        reason: str,
        candidates: tuple[CatalogSeedResolutionCandidate, ...],
    ) -> None:
        issue = CatalogSeedResolutionIssue(
            recipe_index=recipe_index,
            recipe_key=recipe_key,
            ingredient_index=ingredient_index,
            ingredient_name=ingredient_name,
            normalized_name=normalized_name,
            reason=reason,
            candidates=candidates,
        )
        raise CatalogSeedResolutionError(issue)


def _candidate_from_search_row(
    row: _FoodReferenceSearchRow,
    score: float,
) -> CatalogSeedResolutionCandidate:
    return CatalogSeedResolutionCandidate(
        food_reference_id=row.food_reference_id,
        name=row.name,
        name_normalized=row.name_normalized,
        source=row.source,
        is_verified=row.is_verified,
        score=score,
    )


def _projection_from_search_row(
    row: _FoodReferenceSearchRow,
) -> FoodReferenceNutritionProjection:
    return FoodReferenceNutritionProjection(
        id=row.food_reference_id,
        name=row.name,
        source=row.source,
        is_verified=row.is_verified,
        protein_100g=row.protein_100g,
        carbs_100g=row.carbs_100g,
        fat_100g=row.fat_100g,
        fiber_100g=row.fiber_100g,
        sugar_100g=row.sugar_100g,
        density_g_ml=row.density_g_ml,
        servings=[],
    )


def _candidate_score(normalized_name: str, row: _FoodReferenceSearchRow) -> float:
    candidate_name = row.name_normalized or normalize_food_name(row.name)
    sequence = SequenceMatcher(None, normalized_name, candidate_name).ratio()
    source_tokens = set(normalized_name.split())
    candidate_tokens = set(candidate_name.split())
    overlap = (
        len(source_tokens.intersection(candidate_tokens)) / len(source_tokens)
        if source_tokens
        else 0.0
    )
    extra_token_penalty = max(0, len(candidate_tokens) - len(source_tokens)) * 0.03
    return max(0.0, min(1.0, (sequence * 0.7) + (overlap * 0.3) - extra_token_penalty))


def _auto_resolved_candidate(
    candidates: list[CatalogSeedResolutionCandidate],
    threshold: float | None,
    *,
    allow_unverified: bool = False,
) -> CatalogSeedResolutionCandidate | None:
    if threshold is None:
        return None
    eligible = (
        candidates
        if allow_unverified
        else [candidate for candidate in candidates if candidate.is_verified]
    )
    if not eligible:
        return None
    top = eligible[0]
    runner_up = eligible[1].score if len(eligible) > 1 else 0.0
    if allow_unverified and threshold <= 0:
        return top
    if top.score >= threshold and top.score - runner_up >= 0.08:
        return top
    return None


def _content_hash(
    recipe: dict[str, Any],
    ingredients: list[ResolvedIngredientQuantity],
) -> str:
    payload = {
        "name": str(recipe["name"]).strip(),
        "cuisine": str(recipe["cuisine"]).strip(),
        "description": _optional_string(recipe.get("description")),
        "image_url": _optional_string(recipe.get("image_url")),
        "meal_types": sorted(recipe["meal_types"]),
        "ingredients": [
            {
                "food_reference_id": item.food_reference_id,
                "quantity": round(item.quantity, 4),
                "unit": item.unit,
            }
            for item in ingredients
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
