import importlib.util
from pathlib import Path
from types import SimpleNamespace

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "generate_catalog_meal_images.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "generate_catalog_meal_images", _SCRIPT_PATH
)
assert _SPEC is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)
build_catalog_meal_image_prompt = _MODULE.build_catalog_meal_image_prompt


def test_build_catalog_meal_image_prompt_includes_meal_and_ingredients():
    meal = SimpleNamespace(
        name="Pho Ga",
        cuisine="vietnamese",
        ingredients=[
            SimpleNamespace(display_name="Rice noodles"),
            SimpleNamespace(display_name="Chicken"),
        ],
    )

    prompt = build_catalog_meal_image_prompt(meal)

    assert "Pho Ga" in prompt
    assert "vietnamese" in prompt
    assert "Chicken" in prompt
    assert "Rice noodles" in prompt
    assert "no text" in prompt
