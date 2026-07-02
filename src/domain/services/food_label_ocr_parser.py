"""Deterministic parser for OCR text from Nutrition Facts labels."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FoodLabelOcrParseResult:
    structured_data: dict | None = None
    failure_reasons: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.structured_data is not None and not self.failure_reasons


class FoodLabelOcrParser:
    """Parse common US Nutrition Facts OCR lines into the food-label contract."""

    _NUMBER = r"(\d+(?:\.\d+)?)"
    _MACRO_ALIASES = {
        "fat_g": ("total fat", "fat"),
        "carbs_g": ("total carbohydrate", "total carb", "carbohydrate"),
        "fiber_g": ("dietary fiber", "fiber"),
        "sugar_g": ("total sugars", "sugars", "sugar"),
        "protein_g": ("protein",),
    }

    def parse(self, ocr_lines: list[str] | None) -> FoodLabelOcrParseResult:
        lines = self._clean_lines(ocr_lines)
        if len(lines) < 4:
            return FoodLabelOcrParseResult(failure_reasons=["ocr_text_too_sparse"])

        reasons: list[str] = []
        serving_size = self._parse_serving_size(lines)
        if not serving_size:
            reasons.append("missing_serving_size")

        servings_per_package = self._parse_servings_per_package(lines)
        if servings_per_package is None:
            reasons.append("missing_servings_per_package")

        macros, macro_reasons = self._parse_macros(lines)
        reasons.extend(macro_reasons)

        label_calories = self._parse_calories(lines)
        if label_calories is not None and not self._calories_match_macros(
            label_calories, macros
        ):
            reasons.append("conflicting_label_calories")

        if reasons:
            return FoodLabelOcrParseResult(failure_reasons=reasons)

        product_name = self._parse_product_name(lines)
        return FoodLabelOcrParseResult(
            structured_data={
                "is_food_label": True,
                "product_name": product_name or "Scanned Food Label",
                "brand": None,
                "serving_size": serving_size,
                "servings_per_package": servings_per_package,
                "label_calories_per_serving": label_calories,
                "macros_per_serving": macros,
                "confidence": 0.88,
                "label_notes": ["Parsed from OCR text."],
            }
        )

    def _clean_lines(self, ocr_lines: list[str] | None) -> list[str]:
        if not ocr_lines:
            return []
        cleaned: list[str] = []
        for line in ocr_lines:
            text = re.sub(r"\s+", " ", str(line)).strip()
            if text:
                cleaned.append(text)
        return cleaned[:80]

    def _parse_serving_size(self, lines: list[str]) -> dict | None:
        for line in lines:
            lower = line.lower()
            if "serving size" not in lower:
                continue
            grams = self._first_number_before_unit(line, "g")
            if grams is None:
                continue
            display = line.split(":", 1)[-1].strip()
            display = re.sub(r"(?i)^serving size\s*", "", display).strip()
            return {"display_text": display or f"{grams:g}g", "grams": grams}
        return None

    def _parse_servings_per_package(self, lines: list[str]) -> float | None:
        patterns = (
            rf"(?:about\s+)?{self._NUMBER}\s+servings?\s+per\s+(?:container|package)",
            rf"servings?\s+per\s+(?:container|package)\s*(?:about\s*)?{self._NUMBER}",
        )
        for line in lines:
            lower = line.lower()
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    return float(match.group(1))
        return None

    def _parse_macros(self, lines: list[str]) -> tuple[dict, list[str]]:
        macros: dict[str, float] = {}
        reasons: list[str] = []
        for field_name, aliases in self._MACRO_ALIASES.items():
            values = [
                value
                for line in lines
                if (value := self._parse_macro_line(line, aliases)) is not None
            ]
            if not values:
                if field_name in {"fiber_g", "sugar_g"}:
                    macros[field_name] = 0.0
                else:
                    reasons.append(f"missing_{field_name}")
                continue
            if self._has_conflict(values):
                reasons.append(f"conflicting_{field_name}")
                continue
            macros[field_name] = values[0]
        return macros, reasons

    def _parse_macro_line(self, line: str, aliases: tuple[str, ...]) -> float | None:
        lower = line.lower()
        if not any(alias in lower for alias in aliases):
            return None
        if "calories from fat" in lower:
            return None
        match = re.search(r"(?:less than\s*)?(\d+(?:\.\d+)?)\s*g\b", lower)
        if not match:
            return None
        value = float(match.group(1))
        if "less than" in lower:
            return min(value, 0.5)
        return value

    def _parse_calories(self, lines: list[str]) -> float | None:
        for line in lines:
            lower = line.lower()
            if "calories from fat" in lower or "calorie diet" in lower:
                continue
            match = re.search(rf"\bcalories\b\s*{self._NUMBER}", lower)
            if match:
                return float(match.group(1))
        return None

    def _calories_match_macros(self, label_calories: float, macros: dict) -> bool:
        if not {"protein_g", "carbs_g", "fat_g"}.issubset(macros):
            return True
        fiber = float(macros.get("fiber_g", 0.0))
        net_carbs = max(0.0, float(macros["carbs_g"]) - fiber)
        derived = (
            float(macros["protein_g"]) * 4
            + net_carbs * 4
            + fiber * 2
            + float(macros["fat_g"]) * 9
        )
        tolerance = max(50.0, label_calories * 0.35)
        return abs(label_calories - derived) <= tolerance

    def _parse_product_name(self, lines: list[str]) -> str | None:
        skip_terms = (
            "nutrition facts",
            "serving",
            "amount per",
            "calories",
            "daily value",
            "total fat",
            "sodium",
            "carbohydrate",
            "fiber",
            "sugar",
        )
        for line in lines[:6]:
            lower = line.lower()
            if not any(term in lower for term in skip_terms) and len(line) <= 80:
                return line
        return None

    def _first_number_before_unit(self, text: str, unit: str) -> float | None:
        match = re.search(rf"{self._NUMBER}\s*{re.escape(unit)}\b", text.lower())
        return float(match.group(1)) if match else None

    def _has_conflict(self, values: list[float]) -> bool:
        if len(values) < 2:
            return False
        first = values[0]
        return any(abs(value - first) > max(0.5, first * 0.15) for value in values[1:])
