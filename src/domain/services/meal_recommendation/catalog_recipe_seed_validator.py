"""Validation helpers for catalog recipe seed manifests."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

ALLOWED_SOURCE_TYPES = frozenset({"commissioned"})
REQUIRED_CUISINES = ("vietnamese", "japanese", "korean")
REQUIRED_MEAL_TYPES = ("breakfast", "lunch", "dinner")
PRODUCTION_CUISINE_COUNTS = {
    "vietnamese": 60,
    "japanese": 60,
    "korean": 60,
}


@dataclass(frozen=True)
class CatalogSeedValidationResult:
    """Validation report for a catalog recipe manifest."""

    manifest_digest: str
    recipe_count: int
    errors: tuple[str, ...] = field(default_factory=tuple)
    coverage: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_catalog_seed_manifest(
    manifest: dict[str, Any],
    *,
    expected_recipe_count: int = 180,
    min_per_cuisine_meal_type: int = 5,
    expected_cuisine_counts: dict[str, int] | None = PRODUCTION_CUISINE_COUNTS,
) -> CatalogSeedValidationResult:
    """Validate catalog recipe seed manifest before any DB writes."""

    errors: list[str] = []
    recipes = manifest.get("recipes")
    if not isinstance(recipes, list):
        return CatalogSeedValidationResult(
            manifest_digest=manifest_digest(manifest),
            recipe_count=0,
            errors=("recipes must be an array",),
        )

    declared_expected = manifest.get("expected_recipe_count", expected_recipe_count)
    if declared_expected != expected_recipe_count:
        errors.append(
            f"expected_recipe_count must be {expected_recipe_count}, "
            f"got {declared_expected}"
        )
    if len(recipes) != expected_recipe_count:
        errors.append(f"recipe count must be {expected_recipe_count}, got {len(recipes)}")

    keys: Counter[str] = Counter()
    cuisine_counts: Counter[str] = Counter()
    coverage: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for index, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            errors.append(f"recipes[{index}] must be an object")
            continue
        _validate_recipe(recipe, index, errors, keys, coverage, cuisine_counts)

    for recipe_key, count in keys.items():
        if count > 1:
            errors.append(f"duplicate recipe_key: {recipe_key}")

    if expected_cuisine_counts is not None:
        for cuisine, expected_count in expected_cuisine_counts.items():
            actual_count = cuisine_counts[cuisine]
            if actual_count != expected_count:
                errors.append(
                    f"cuisine {cuisine} requires {expected_count} recipes, "
                    f"got {actual_count}"
                )

    coverage_dict = {
        cuisine: {meal_type: counts.get(meal_type, 0) for meal_type in REQUIRED_MEAL_TYPES}
        for cuisine, counts in coverage.items()
    }
    for cuisine in REQUIRED_CUISINES:
        for meal_type in REQUIRED_MEAL_TYPES:
            count = coverage[cuisine][meal_type]
            if count < min_per_cuisine_meal_type:
                errors.append(
                    f"coverage {cuisine}/{meal_type} requires "
                    f"{min_per_cuisine_meal_type}, got {count}"
                )

    return CatalogSeedValidationResult(
        manifest_digest=manifest_digest(manifest),
        recipe_count=len(recipes),
        errors=tuple(errors),
        coverage=coverage_dict,
    )


def manifest_digest(manifest: dict[str, Any]) -> str:
    """Return a stable SHA-256 digest for the manifest content."""

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_recipe(
    recipe: dict[str, Any],
    index: int,
    errors: list[str],
    keys: Counter[str],
    coverage: defaultdict[str, Counter[str]],
    cuisine_counts: Counter[str],
) -> None:
    recipe_key = _string(recipe.get("recipe_key"))
    if recipe_key is None:
        errors.append(f"recipes[{index}].recipe_key is required")
    else:
        keys[recipe_key] += 1

    cuisine = _string(recipe.get("cuisine"))
    if cuisine not in REQUIRED_CUISINES:
        errors.append(f"recipes[{index}].cuisine is invalid: {cuisine}")
    else:
        cuisine_counts[cuisine] += 1

    meal_types = recipe.get("meal_types")
    if not isinstance(meal_types, list) or not meal_types:
        errors.append(f"recipes[{index}].meal_types must be a non-empty array")
        meal_types = []
    for meal_type in meal_types:
        if meal_type not in REQUIRED_MEAL_TYPES:
            errors.append(f"recipes[{index}].meal_types has invalid value: {meal_type}")
        elif cuisine is not None:
            coverage[cuisine][meal_type] += 1

    if _string(recipe.get("name")) is None:
        errors.append(f"recipes[{index}].name is required")

    _validate_rights(recipe.get("rights"), index, errors)
    _validate_sources(recipe.get("sources"), index, errors)
    _validate_ingredients(recipe.get("ingredients"), index, errors)
    _validate_recipe_macro_totals(recipe, index, errors)


def _validate_rights(rights: Any, index: int, errors: list[str]) -> None:
    if not isinstance(rights, dict):
        errors.append(f"recipes[{index}].rights must be an object")
        return
    if rights.get("status") != "approved":
        errors.append(f"recipes[{index}].rights.status must be approved")
    if _string(rights.get("agreement_identifier")) is None:
        errors.append(f"recipes[{index}].rights.agreement_identifier is required")
    if _string(rights.get("approver")) is None:
        errors.append(f"recipes[{index}].rights.approver is required")


def _validate_sources(sources: Any, index: int, errors: list[str]) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"recipes[{index}].sources must be a non-empty array")
        return
    for source_index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"recipes[{index}].sources[{source_index}] must be an object")
            continue
        source_type = source.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"recipes[{index}].sources[{source_index}].source_type "
                f"is not allowlisted: {source_type}"
            )


def _validate_ingredients(ingredients: Any, index: int, errors: list[str]) -> None:
    if not isinstance(ingredients, list) or not ingredients:
        errors.append(f"recipes[{index}].ingredients must be a non-empty array")
        return
    for ingredient_index, ingredient in enumerate(ingredients):
        if not isinstance(ingredient, dict):
            errors.append(
                f"recipes[{index}].ingredients[{ingredient_index}] must be an object"
            )
            continue
        if not isinstance(ingredient.get("food_reference_id"), int):
            errors.append(
                f"recipes[{index}].ingredients[{ingredient_index}].food_reference_id "
                "is required"
            )
        _validate_non_negative_macro(
            ingredient,
            index,
            ingredient_index,
            "protein_g",
            errors,
        )
        carbs = _validate_non_negative_macro(
            ingredient,
            index,
            ingredient_index,
            "carbs_g",
            errors,
        )
        _validate_non_negative_macro(ingredient, index, ingredient_index, "fat_g", errors)
        fiber = _validate_non_negative_macro(
            ingredient,
            index,
            ingredient_index,
            "fiber_g",
            errors,
        )
        sugar = _validate_non_negative_macro(
            ingredient,
            index,
            ingredient_index,
            "sugar_g",
            errors,
        )
        if carbs is not None and fiber is not None and fiber > carbs:
            errors.append(
                f"recipes[{index}].ingredients[{ingredient_index}].fiber_g exceeds carbs_g"
            )
        if carbs is not None and sugar is not None and sugar > carbs:
            errors.append(
                f"recipes[{index}].ingredients[{ingredient_index}].sugar_g exceeds carbs_g"
            )
        resolved_grams = ingredient.get("resolved_grams")
        if not isinstance(resolved_grams, int | float) or resolved_grams <= 0:
            errors.append(
                f"recipes[{index}].ingredients[{ingredient_index}].resolved_grams "
                "must be positive"
            )


def _validate_recipe_macro_totals(
    recipe: dict[str, Any],
    index: int,
    errors: list[str],
) -> None:
    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list):
        return

    totals = {
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
    }
    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            return
        for key in totals:
            value = ingredient.get(key, 0.0)
            if not isinstance(value, int | float):
                return
            totals[key] += float(value)

    for key, expected in totals.items():
        supplied = recipe.get(key)
        if supplied is not None and not isinstance(supplied, int | float):
            errors.append(f"recipes[{index}].{key} must be numeric")
        elif supplied is not None and not _close_enough(float(supplied), expected):
            errors.append(
                f"recipes[{index}].{key} must match ingredient sum "
                f"{expected:.2f}, got {supplied}"
            )

    supplied_calories = recipe.get("calories")
    if supplied_calories is not None and not isinstance(supplied_calories, int | float):
        errors.append(f"recipes[{index}].calories must be numeric")
    elif supplied_calories is not None:
        derived_calories = round(
            totals["protein_g"] * 4
            + max(totals["carbs_g"] - totals["fiber_g"], 0) * 4
            + totals["fiber_g"] * 2
            + totals["fat_g"] * 9
        )
        if not _close_enough(float(supplied_calories), derived_calories, tolerance=1.0):
            errors.append(
                f"recipes[{index}].calories must match ingredient-derived "
                f"{derived_calories}, got {supplied_calories}"
            )


def _validate_non_negative_macro(
    ingredient: dict[str, Any],
    recipe_index: int,
    ingredient_index: int,
    key: str,
    errors: list[str],
) -> float | None:
    value = ingredient.get(key, 0.0)
    if not isinstance(value, int | float) or value < 0:
        errors.append(
            f"recipes[{recipe_index}].ingredients[{ingredient_index}].{key} "
            "must be non-negative"
        )
        return None
    return float(value)


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _close_enough(left: float, right: float, *, tolerance: float = 0.01) -> bool:
    return abs(left - right) <= tolerance
