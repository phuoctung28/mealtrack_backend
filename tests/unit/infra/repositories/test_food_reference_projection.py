from unittest.mock import MagicMock

from src.infra.database.models.food_reference_nutrient import (
    FoodReferenceNutrientModel,
)
from src.infra.repositories.food_reference_projection import (
    food_reference_model_to_dict,
)


def _make_food_reference_model(name_normalized: str) -> MagicMock:
    """Build a minimal FoodReferenceModel-like mock."""
    model = MagicMock()
    model.name_normalized = name_normalized
    model.id = 1
    model.barcode = None
    model.name = "chicken breast"
    model.name_vi = None
    model.brand = None
    model.category = None
    model.region = "global"
    model.fdc_id = None
    model.protein_100g = 23.0
    model.carbs_100g = 0.0
    model.fat_100g = 2.5
    model.fiber_100g = 0.0
    model.sugar_100g = 0.0
    model.serving_size_rows = []
    model.serving_sizes = None
    model.density = 1.0
    model.serving_size = None
    model.nutrient_rows = []
    model.extra_nutrients = None
    model.source = "fatsecret"
    model.is_verified = False
    model.image_url = None
    return model


def test_food_reference_nutrient_projection_preserves_legacy_scalar_shape():
    model = _make_food_reference_model("spinach")
    model.extra_nutrients = {"calcium_mg": 99}
    model.nutrient_rows = [
        FoodReferenceNutrientModel(
            nutrient_key="calcium_mg",
            amount=120.0,
            unit="mg",
        )
    ]

    result = food_reference_model_to_dict(model)

    assert result["extra_nutrients"]["calcium_mg"] == 120.0


def test_food_reference_nutrient_projection_preserves_legacy_object_shape():
    model = _make_food_reference_model("spinach")
    model.extra_nutrients = {
        "calcium_mg": {"amount": 99, "unit": "mg", "source": "old"}
    }
    model.nutrient_rows = [
        FoodReferenceNutrientModel(
            nutrient_key="calcium_mg",
            amount=120.0,
            unit="mg",
        )
    ]

    result = food_reference_model_to_dict(model)

    assert result["extra_nutrients"]["calcium_mg"] == {
        "amount": 120.0,
        "unit": "mg",
        "source": "old",
    }
