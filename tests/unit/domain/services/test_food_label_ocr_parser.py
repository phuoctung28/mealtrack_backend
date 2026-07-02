"""Tests for deterministic Nutrition Facts OCR parsing."""

import pytest

from src.domain.services.food_label_ocr_parser import FoodLabelOcrParser


def _clean_label_lines() -> list[str]:
    return [
        "ACME Protein Bar",
        "Nutrition Facts",
        "8 servings per container",
        "Serving size 1 bar (55g)",
        "Calories 210",
        "Total Fat 7g",
        "Total Carbohydrate 24g",
        "Dietary Fiber 5g",
        "Total Sugars 8g",
        "Protein 12g",
    ]


def test_parse_clean_us_label_succeeds():
    result = FoodLabelOcrParser().parse(_clean_label_lines())

    assert result.succeeded is True
    data = result.structured_data
    assert data is not None
    assert data["product_name"] == "ACME Protein Bar"
    assert data["serving_size"]["grams"] == pytest.approx(55)
    assert data["servings_per_package"] == pytest.approx(8)
    assert data["macros_per_serving"]["protein_g"] == pytest.approx(12)
    assert data["label_calories_per_serving"] == pytest.approx(210)


def test_parse_missing_required_macro_fails():
    lines = [
        line for line in _clean_label_lines() if not line.startswith("Protein")
    ]

    result = FoodLabelOcrParser().parse(lines)

    assert result.succeeded is False
    assert "missing_protein_g" in result.failure_reasons


def test_parse_conflicting_macro_values_fails():
    result = FoodLabelOcrParser().parse(
        [*_clean_label_lines(), "Total Fat 20g"]
    )

    assert result.succeeded is False
    assert "conflicting_fat_g" in result.failure_reasons


def test_parse_sparse_ocr_text_fails():
    result = FoodLabelOcrParser().parse(["Nutrition Facts", "Calories 120"])

    assert result.succeeded is False
    assert result.failure_reasons == ["ocr_text_too_sparse"]


def test_parse_conflicting_label_calories_fails():
    lines = [
        "ACME Protein Bar",
        "Nutrition Facts",
        "8 servings per container",
        "Serving size 1 bar (55g)",
        "Calories 900",
        "Total Fat 7g",
        "Total Carbohydrate 24g",
        "Dietary Fiber 5g",
        "Total Sugars 8g",
        "Protein 12g",
    ]

    result = FoodLabelOcrParser().parse(lines)

    assert result.succeeded is False
    assert "conflicting_label_calories" in result.failure_reasons
