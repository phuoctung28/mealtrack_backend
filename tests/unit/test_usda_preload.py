import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "preload_usda_food_reference.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "preload_usda_food_reference", _MODULE_PATH
)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)
usda_row_to_food_reference = _MODULE.usda_row_to_food_reference


def test_maps_usda_foundation_row_to_per100g():
    row = {
        "description": "Chicken breast, raw",
        "foodNutrients": [
            {"nutrientName": "Protein", "value": 22.5},
            {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
            {"nutrientName": "Total lipid (fat)", "value": 2.6},
            {"nutrientName": "Fiber, total dietary", "value": 0.0},
        ],
    }

    output = usda_row_to_food_reference(row)

    assert output["name"] == "Chicken breast, raw"
    assert output["protein_100g"] == 22.5
    assert output["fat_100g"] == 2.6
    assert output["source"] == "usda"
    assert output["is_verified"] is True
