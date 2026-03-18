"""
Standardized output schema for all VN food scrapers.
All scrapers produce FoodEntry instances serialized to JSON.
"""
import json
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class FoodEntry:
    name: str                                    # English name
    name_vi: str                                 # Vietnamese name (required for VN foods)
    category: str                                # Standardized English category
    region: str = "VN"
    source: str = ""                             # nin_vn | vn_fct_pdf | openfoodfacts | ttytyenlac
    protein_100g: float = 0.0
    carbs_100g: float = 0.0
    fat_100g: float = 0.0
    fiber_100g: float = 0.0
    sugar_100g: float = 0.0
    density: float = 1.0                         # g/ml for volume→weight conversion
    extra_nutrients: dict[str, Any] = field(default_factory=dict)  # calcium_mg, iron_mg, etc.
    barcode: str | None = None
    brand: str | None = None
    image_url: str | None = None

    def validate(self) -> list[str]:
        """Return list of warning strings; empty means valid."""
        warnings: list[str] = []
        macro_sum = self.protein_100g + self.carbs_100g + self.fat_100g
        if macro_sum > 100:
            warnings.append(
                f"Macro sum {macro_sum:.1f}g exceeds 100g/100g "
                f"(P={self.protein_100g}, C={self.carbs_100g}, F={self.fat_100g})"
            )
        for field_name, val in [
            ("protein_100g", self.protein_100g),
            ("carbs_100g", self.carbs_100g),
            ("fat_100g", self.fat_100g),
            ("fiber_100g", self.fiber_100g),
            ("sugar_100g", self.sugar_100g),
        ]:
            if val < 0:
                warnings.append(f"{field_name} is negative: {val}")
        if not self.name_vi and self.region == "VN":
            warnings.append("name_vi is required for VN-sourced foods")
        if not self.name:
            warnings.append("name (English) is empty")
        return warnings

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FoodEntry":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def save_entries(entries: list[FoodEntry], filepath: str | Path) -> None:
    """Serialize list of FoodEntry to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            [e.to_dict() for e in entries],
            f,
            ensure_ascii=False,
            indent=2,
        )


def load_entries(filepath: str | Path) -> list[FoodEntry]:
    """Load FoodEntry list from a JSON file."""
    with open(Path(filepath), "r", encoding="utf-8") as f:
        raw: list[dict[str, Any]] = json.load(f)
    return [FoodEntry.from_dict(item) for item in raw]
