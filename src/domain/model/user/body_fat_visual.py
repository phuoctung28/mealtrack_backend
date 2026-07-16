"""Immutable catalog rules for visual body-fat selections."""

from typing import Final

BODY_FAT_VISUAL_SCHEMA_VERSION: Final = 1
BODY_FAT_VISUAL_RANGE_CATALOG_VERSION: Final = 1

BODY_FAT_VISUAL_RANGES_BY_SEX: Final[dict[str, frozenset[str]]] = {
    "male": frozenset(
        {
            "male_8_12",
            "male_13_16",
            "male_17_20",
            "male_21_24",
            "male_25_29",
            "male_30_plus",
        }
    ),
    "female": frozenset(
        {
            "female_18_21",
            "female_22_25",
            "female_26_30",
            "female_31_35",
            "female_36_39",
            "female_40_plus",
        }
    ),
}

BODY_FAT_VISUAL_RANGE_IDS: Final = frozenset().union(
    *BODY_FAT_VISUAL_RANGES_BY_SEX.values()
)


def is_valid_visual_range_for_sex(sex: str, range_id: str) -> bool:
    """Return whether a catalog range belongs to the selected sex."""
    return range_id in BODY_FAT_VISUAL_RANGES_BY_SEX.get(sex, frozenset())
