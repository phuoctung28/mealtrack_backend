"""Enums for movement domain constrained values."""

from enum import Enum


class MovementIntensity(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HARD = "hard"


class MovementSource(str, Enum):
    MANUAL = "manual"
    APPLE_HEALTH = "apple_health"
