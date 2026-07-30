import pytest

from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
    FoodReferenceServingProjection,
)
from src.domain.services.meal_recommendation.ingredient_quantity_conversion_service import (
    IngredientQuantityConversionError,
    IngredientQuantityConversionService,
)


def _reference(**overrides) -> FoodReferenceNutritionProjection:
    data = {
        "id": 42,
        "name": "Chicken breast",
        "source": "catalog_seed",
        "is_verified": True,
        "protein_100g": 31.0,
        "carbs_100g": 0.0,
        "fat_100g": 3.6,
        "fiber_100g": 0.0,
        "sugar_100g": 0.0,
        "density_g_ml": 1.0,
        "servings": [
            FoodReferenceServingProjection(
                name="piece",
                grams=120.0,
                milliliters=None,
                is_default=True,
            )
        ],
    }
    data.update(overrides)
    return FoodReferenceNutritionProjection(**data)


def test_resolves_grams_and_scales_macros_with_derived_calories():
    result = IngredientQuantityConversionService().resolve(
        reference=_reference(),
        quantity=150,
        unit="g",
    )

    assert result.grams == 150
    assert result.protein == pytest.approx(46.5)
    assert result.fat == pytest.approx(5.4)
    assert result.calories == pytest.approx(46.5 * 4 + 5.4 * 9)
    assert result.food_reference_id == 42


def test_resolves_milliliters_using_food_specific_density():
    reference = _reference(name="Soy sauce", density_g_ml=1.2)

    result = IngredientQuantityConversionService().resolve(
        reference=reference,
        quantity=50,
        unit="ml",
    )

    assert result.grams == pytest.approx(60)


def test_resolves_named_serving_from_food_specific_projection():
    result = IngredientQuantityConversionService().resolve(
        reference=_reference(),
        quantity=2,
        unit="piece",
    )

    assert result.grams == pytest.approx(240)
    assert result.protein == pytest.approx(74.4)


def test_rejects_unverified_food_reference():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(is_verified=False),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "food_reference_not_verified"


def test_rejects_unapproved_source_until_an_admin_verifies_that_reference():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(source="ai_estimate", is_verified=False),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "food_reference_not_verified"


def test_accepts_admin_verified_reference_from_an_unapproved_source():
    result = IngredientQuantityConversionService().resolve(
        reference=_reference(source="ai_estimate", is_verified=True),
        quantity=100,
        unit="g",
    )

    assert result.food_reference_id == 42


def test_review_mode_still_rejects_an_unapproved_unverified_source():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService(allow_unverified=True).resolve(
            reference=_reference(source="ai_estimate", is_verified=False),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "food_reference_source_not_approved"


def test_accepts_existing_usda_fdc_source_name():
    result = IngredientQuantityConversionService().resolve(
        reference=_reference(source="usda_fdc"),
        quantity=100,
        unit="g",
    )

    assert result.food_reference_id == 42


def test_rejects_ambiguous_named_serving():
    reference = _reference(
        servings=[
            FoodReferenceServingProjection(
                name="bowl",
                grams=200,
                milliliters=None,
                is_default=True,
            ),
            FoodReferenceServingProjection(
                name="bowl",
                grams=250,
                milliliters=None,
                is_default=False,
            ),
        ]
    )

    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=reference,
            quantity=1,
            unit="bowl",
        )

    assert exc.value.code == "ambiguous_serving_unit"


def test_rejects_missing_required_macros():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(protein_100g=None),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "incomplete_macro_snapshot"


def test_rejects_unknown_unit_without_silent_fallback():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(),
            quantity=1,
            unit="handful",
        )

    assert exc.value.code == "unresolved_quantity_unit"


def test_rejects_invalid_density_for_volume_conversion():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(density_g_ml=None),
            quantity=50,
            unit="ml",
        )

    assert exc.value.code == "invalid_density"


def test_rejects_implausible_resolved_grams():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(),
            quantity=11,
            unit="kg",
        )

    assert exc.value.code == "implausible_resolved_grams"


def test_rejects_implausible_macro_snapshot():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(protein_100g=80, carbs_100g=40, fat_100g=10),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "implausible_macro_snapshot"


def test_rejects_fiber_or_sugar_exceeding_carbs():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(carbs_100g=5, fiber_100g=6),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "implausible_macro_snapshot"


def test_rejects_combined_fiber_and_sugar_exceeding_carbs():
    with pytest.raises(IngredientQuantityConversionError) as exc:
        IngredientQuantityConversionService().resolve(
            reference=_reference(carbs_100g=10, fiber_100g=6, sugar_100g=6),
            quantity=100,
            unit="g",
        )

    assert exc.value.code == "implausible_macro_snapshot"


def test_display_only_garnish_does_not_require_food_reference_or_macros():
    result = IngredientQuantityConversionService().resolve(
        reference=None,
        quantity=1,
        unit="sprig",
        display_only=True,
        display_name="Cilantro garnish",
    )

    assert result.display_only is True
    assert result.food_reference_id is None
    assert result.grams == 0
    assert result.calories == 0
