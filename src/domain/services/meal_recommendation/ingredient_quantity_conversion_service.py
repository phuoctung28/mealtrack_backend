"""Strict recipe ingredient quantity conversion for catalog publication."""

from dataclasses import dataclass
from typing import cast

from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
    FoodReferenceServingProjection,
)

_WEIGHT_UNITS_TO_GRAMS = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "oz": 28.349523125,
    "ounce": 28.349523125,
    "ounces": 28.349523125,
    "lb": 453.59237,
    "pound": 453.59237,
    "pounds": 453.59237,
}
_VOLUME_UNITS_TO_ML = {
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "millilitre": 1.0,
    "millilitres": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "litre": 1000.0,
    "litres": 1000.0,
}
_DEFAULT_APPROVED_SOURCES = frozenset(
    {
        "catalog_seed",
        "commissioned",
        "fatsecret",
        "usda",
        "usda_fdc",
        "verified_seed",
    }
)
_MAX_RESOLVED_GRAMS = 10_000.0
_MAX_DENSITY_G_ML = 3.0


class IngredientQuantityConversionError(ValueError):
    """Typed conversion failure for catalog publication gates."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ResolvedIngredientQuantity:
    """Resolved gram weight and macro snapshot for one recipe ingredient."""

    food_reference_id: int | None
    display_name: str
    quantity: float
    unit: str
    grams: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    calories: float
    display_only: bool = False


class IngredientQuantityConversionService:
    """Convert recipe ingredient quantities without unsafe fallbacks."""

    def __init__(
        self,
        approved_sources: set[str] | frozenset[str] | None = None,
        allow_unverified: bool = False,
        allow_unapproved_sources: bool = False,
        allow_implausible_macros: bool = False,
        allow_common_unit_fallbacks: bool = False,
    ) -> None:
        self._approved_sources = approved_sources or _DEFAULT_APPROVED_SOURCES
        self._allow_unverified = allow_unverified
        self._allow_unapproved_sources = allow_unapproved_sources
        self._allow_implausible_macros = allow_implausible_macros
        self._allow_common_unit_fallbacks = allow_common_unit_fallbacks

    def resolve(
        self,
        *,
        reference: FoodReferenceNutritionProjection | None,
        quantity: float,
        unit: str,
        display_only: bool = False,
        display_name: str | None = None,
    ) -> ResolvedIngredientQuantity:
        """Resolve a recipe quantity to grams and scaled macros."""
        if display_only:
            return ResolvedIngredientQuantity(
                food_reference_id=None,
                display_name=display_name or (reference.name if reference else ""),
                quantity=quantity,
                unit=unit,
                grams=0.0,
                protein=0.0,
                carbs=0.0,
                fat=0.0,
                fiber=0.0,
                sugar=0.0,
                calories=0.0,
                display_only=True,
            )

        if reference is None:
            raise IngredientQuantityConversionError(
                "food_reference_required",
                "Nutritional recipe ingredients require a food reference.",
            )

        self._validate_reference(reference)
        grams = self._resolve_grams(reference, quantity, unit)
        self._validate_resolved_grams(grams)
        factor = grams / 100.0
        protein_100g = cast(float, reference.protein_100g)
        carbs_100g = cast(float, reference.carbs_100g)
        fat_100g = cast(float, reference.fat_100g)
        protein = protein_100g * factor
        carbs = carbs_100g * factor
        fat = fat_100g * factor
        fiber = (reference.fiber_100g or 0.0) * factor
        sugar = (reference.sugar_100g or 0.0) * factor
        calories = protein * 4 + max(carbs - fiber, 0.0) * 4 + fiber * 2 + fat * 9
        return ResolvedIngredientQuantity(
            food_reference_id=reference.id,
            display_name=display_name or reference.name,
            quantity=quantity,
            unit=unit,
            grams=grams,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            sugar=sugar,
            calories=calories,
        )

    def _validate_reference(self, reference: FoodReferenceNutritionProjection) -> None:
        if not reference.is_verified and not self._allow_unverified:
            raise IngredientQuantityConversionError(
                "food_reference_not_verified",
                f"Food reference {reference.id} is not verified.",
            )
        if (
            reference.source.lower() not in self._approved_sources
            and not reference.is_verified
            and not self._allow_unapproved_sources
        ):
            raise IngredientQuantityConversionError(
                "food_reference_source_not_approved",
                f"Food reference {reference.id} source is not approved.",
            )
        macros = (
            reference.protein_100g,
            reference.carbs_100g,
            reference.fat_100g,
        )
        if any(value is None or value < 0 for value in macros):
            raise IngredientQuantityConversionError(
                "incomplete_macro_snapshot",
                f"Food reference {reference.id} has incomplete macros.",
            )
        protein_100g = cast(float, reference.protein_100g)
        carbs_100g = cast(float, reference.carbs_100g)
        fat_100g = cast(float, reference.fat_100g)
        if (reference.fiber_100g or 0.0) < 0 or (reference.sugar_100g or 0.0) < 0:
            raise IngredientQuantityConversionError(
                "incomplete_macro_snapshot",
                f"Food reference {reference.id} has invalid fiber or sugar.",
            )
        fiber = reference.fiber_100g or 0.0
        sugar = reference.sugar_100g or 0.0
        if not self._allow_implausible_macros and (
            fiber > carbs_100g or sugar > carbs_100g or fiber + sugar > carbs_100g
        ):
            raise IngredientQuantityConversionError(
                "implausible_macro_snapshot",
                f"Food reference {reference.id} fiber or sugar exceeds carbs.",
            )
        macro_mass = protein_100g + carbs_100g + fat_100g
        if macro_mass > 110.0 and not self._allow_implausible_macros:
            raise IngredientQuantityConversionError(
                "implausible_macro_snapshot",
                f"Food reference {reference.id} macros exceed plausible mass.",
            )

    def _resolve_grams(
        self,
        reference: FoodReferenceNutritionProjection,
        quantity: float,
        unit: str,
    ) -> float:
        if quantity <= 0:
            raise IngredientQuantityConversionError(
                "invalid_quantity",
                "Ingredient quantity must be greater than zero.",
            )
        normalized_unit = _normalize_unit(unit)
        if normalized_unit in _WEIGHT_UNITS_TO_GRAMS:
            return quantity * _WEIGHT_UNITS_TO_GRAMS[normalized_unit]
        if normalized_unit in _VOLUME_UNITS_TO_ML:
            density = self._validated_density(reference)
            return quantity * _VOLUME_UNITS_TO_ML[normalized_unit] * density
        fallback_grams = self._common_unit_fallback_grams(reference, normalized_unit)
        if fallback_grams is not None:
            return quantity * fallback_grams
        serving = self._find_serving(reference.servings, normalized_unit)
        if serving.grams is not None and serving.grams > 0:
            return quantity * serving.grams
        if serving.milliliters is not None and serving.milliliters > 0:
            density = self._validated_density(reference)
            return quantity * serving.milliliters * density
        raise IngredientQuantityConversionError(
            "unresolved_quantity_unit",
            f"Serving '{unit}' has no usable grams or milliliters.",
        )

    def _common_unit_fallback_grams(
        self,
        reference: FoodReferenceNutritionProjection,
        normalized_unit: str,
    ) -> float | None:
        if not self._allow_common_unit_fallbacks:
            return None
        if normalized_unit not in {"each", "piece", "unit"}:
            return None
        if "egg" in reference.name.lower():
            return 50.0
        return None

    def _validated_density(self, reference: FoodReferenceNutritionProjection) -> float:
        density = reference.density_g_ml
        if density is None or density <= 0 or density > _MAX_DENSITY_G_ML:
            raise IngredientQuantityConversionError(
                "invalid_density",
                f"Food reference {reference.id} has invalid density.",
            )
        return density

    def _find_serving(
        self,
        servings: list[FoodReferenceServingProjection],
        normalized_unit: str,
    ) -> FoodReferenceServingProjection:
        matches = [
            serving
            for serving in servings
            if _normalize_unit(serving.name) == normalized_unit
        ]
        if not matches:
            raise IngredientQuantityConversionError(
                "unresolved_quantity_unit",
                f"Unit '{normalized_unit}' is not resolvable for this food.",
            )
        weights = {
            (
                round(serving.grams, 6) if serving.grams is not None else None,
                (
                    round(serving.milliliters, 6)
                    if serving.milliliters is not None
                    else None
                ),
            )
            for serving in matches
        }
        if len(weights) > 1:
            raise IngredientQuantityConversionError(
                "ambiguous_serving_unit",
                f"Serving '{normalized_unit}' maps to multiple weights.",
            )
        return matches[0]

    def _validate_resolved_grams(self, grams: float) -> None:
        if grams <= 0:
            raise IngredientQuantityConversionError(
                "invalid_resolved_grams",
                "Resolved ingredient grams must be greater than zero.",
            )
        if grams > _MAX_RESOLVED_GRAMS:
            raise IngredientQuantityConversionError(
                "implausible_resolved_grams",
                "Resolved ingredient grams exceed the publication limit.",
            )


def _normalize_unit(unit: str) -> str:
    return " ".join((unit or "").lower().strip().split())
