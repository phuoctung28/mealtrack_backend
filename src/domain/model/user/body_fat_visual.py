"""Domain model and immutable catalog rules for visual body-fat selections."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final
from uuid import UUID, uuid4

BODY_FAT_VISUAL_SCHEMA_VERSION: Final = 1
BODY_FAT_VISUAL_RANGE_CATALOG_VERSION: Final = 1

BODY_FAT_VISUAL_RANGES_BY_SEX: Final[dict[str, tuple[str, ...]]] = {
    "male": (
        "male_8_12",
        "male_13_16",
        "male_17_20",
        "male_21_24",
        "male_25_29",
        "male_30_plus",
    ),
    "female": (
        "female_18_21",
        "female_22_25",
        "female_26_30",
        "female_31_35",
        "female_36_39",
        "female_40_plus",
    ),
}

BODY_FAT_VISUAL_RANGE_IDS: Final = frozenset().union(
    *BODY_FAT_VISUAL_RANGES_BY_SEX.values()
)


@dataclass(frozen=True, kw_only=True)
class BodyFatVisualProfileSelection:
    """One append-only visual body-fat selection."""

    user_id: str
    schema_version: int
    range_catalog_version: int
    sex_at_selection: str
    start_range_id: str | None
    current_range_id: str
    target_range_id: str | None
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime | None = None


def is_valid_visual_range_for_sex(sex: str, range_id: str) -> bool:
    """Return whether a catalog range belongs to the selected sex."""
    return range_id in BODY_FAT_VISUAL_RANGES_BY_SEX.get(sex, ())


def remap_visual_range_id(
    range_id: str | None, *, source_sex: str, target_sex: str
) -> str | None:
    """Map a visual range to the same ordinal in another sex's catalog."""
    if range_id is None:
        return None

    source_ranges = BODY_FAT_VISUAL_RANGES_BY_SEX[source_sex]
    target_ranges = BODY_FAT_VISUAL_RANGES_BY_SEX[target_sex]
    if len(source_ranges) != len(target_ranges):
        raise ValueError("Visual body-fat catalogs must have matching range counts")

    return target_ranges[source_ranges.index(range_id)]


def remap_visual_profile_selection(
    selection: BodyFatVisualProfileSelection, *, target_sex: str
) -> BodyFatVisualProfileSelection:
    """Create an append-only selection remapped to a new biological sex."""
    return BodyFatVisualProfileSelection(
        user_id=selection.user_id,
        schema_version=selection.schema_version,
        range_catalog_version=selection.range_catalog_version,
        sex_at_selection=target_sex,
        start_range_id=remap_visual_range_id(
            selection.start_range_id,
            source_sex=selection.sex_at_selection,
            target_sex=target_sex,
        ),
        current_range_id=remap_visual_range_id(
            selection.current_range_id,
            source_sex=selection.sex_at_selection,
            target_sex=target_sex,
        ),
        target_range_id=remap_visual_range_id(
            selection.target_range_id,
            source_sex=selection.sex_at_selection,
            target_sex=target_sex,
        ),
    )
