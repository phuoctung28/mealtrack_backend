"""Service for building hydration entries from beverage scan results.

Pure domain helper — no UoW or DB dependency.
The actual DB write stays in the command handler via uow.hydration_entries.add().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_HYDRATION_WEIGHT_ESTIMATE = 0.7   # unknown label: conservative fallback
_HYDRATION_WEIGHT_SUGARY = 0.7     # > 5 g sugar/100 ml: high-sugar
_HYDRATION_WEIGHT_SPORTS = 0.85    # 0–5 g sugar/100 ml: sports/low-sugar
_HYDRATION_WEIGHT_WATER_LIKE = 1.0  # 0 g sugar: effectively water


@dataclass
class BeverageScanParams:
    """Validated parameters derived from a beverage vision scan."""

    user_id: str
    drink_name: str       # stored in drink_name_snapshot
    volume_ml: int
    kcal_total: float     # computed: volume_ml * kcal_per_100ml / 100
    sugar_g_total: float  # computed: volume_ml * sugar_per_100ml / 100
    hydration_weight: float
    image_url: str | None = None
    label_source: str = "estimate"
    emoji: str = "🥤"

    @property
    def credited_ml(self) -> int:
        return int(self.volume_ml * self.hydration_weight)


def compute_hydration_weight(label_source: str, sugar_per_100ml: float) -> float:
    """Return hydration weight for a scanned beverage."""
    if label_source == "estimate":
        return _HYDRATION_WEIGHT_ESTIMATE
    if sugar_per_100ml > 5.0:
        return _HYDRATION_WEIGHT_SUGARY
    if sugar_per_100ml > 0.0:
        return _HYDRATION_WEIGHT_SPORTS
    return _HYDRATION_WEIGHT_WATER_LIKE


def build_beverage_scan_params(
    user_id: str,
    bev_meta: dict,
    image_url: str | None = None,
) -> BeverageScanParams:
    """Build BeverageScanParams from raw beverage_metadata dict."""
    kcal_per_100ml = float(bev_meta.get("kcal_per_100ml") or 0.0)
    sugar_per_100ml = float(bev_meta.get("sugar_per_100ml") or 0.0)
    volume_ml = int(bev_meta.get("volume_ml") or 0)
    label_source = bev_meta.get("label_source", "estimate")

    brand = bev_meta.get("brand") or bev_meta.get("product_name") or "Scanned Drink"
    hydration_weight = compute_hydration_weight(label_source, sugar_per_100ml)

    return BeverageScanParams(
        user_id=user_id,
        drink_name=brand,
        volume_ml=volume_ml,
        kcal_total=round(volume_ml * kcal_per_100ml / 100.0, 1),
        sugar_g_total=round(volume_ml * sugar_per_100ml / 100.0, 1),
        hydration_weight=hydration_weight,
        image_url=image_url,
        label_source=label_source,
    )
