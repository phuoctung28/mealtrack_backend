"""Enums for constrained string fields in the hydration domain."""

from enum import Enum


class DrinkCategory(str, Enum):
    HYDRATION = "hydration"
    CALORIC = "caloric"


class HydrationSource(str, Enum):
    HYDRATION = "hydration"
    CALORIC_DRINK = "caloric_drink"
