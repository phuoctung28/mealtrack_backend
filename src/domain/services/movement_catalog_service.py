"""Backend-owned movement activity catalog and MET values."""

from copy import deepcopy
from typing import Any

_ACTIVITIES: list[dict[str, Any]] = [
    {
        "id": "walking",
        "name": {"en": "Walking", "vi": "Đi bộ"},
        "default_met": 3.8,
        "met": {"light": 3.0, "moderate": 3.8, "hard": 4.8},
        "apple_health_type": "walking",
        "is_custom": False,
    },
    {
        "id": "running",
        "name": {"en": "Running", "vi": "Chạy bộ"},
        "default_met": 8.5,
        "met": {"light": 6.5, "moderate": 8.5, "hard": 10.5},
        "apple_health_type": "running",
        "is_custom": False,
    },
    {
        "id": "cycling",
        "name": {"en": "Cycling", "vi": "Đạp xe"},
        "default_met": 7.0,
        "met": {"light": 4.0, "moderate": 7.0, "hard": 9.0},
        "apple_health_type": "cycling",
        "is_custom": False,
    },
    {
        "id": "gym_strength",
        "name": {"en": "Gym / Strength", "vi": "Tập gym"},
        "default_met": 3.5,
        "met": {"light": 3.5, "moderate": 5.0, "hard": 6.0},
        "apple_health_type": "traditionalStrengthTraining",
        "is_custom": False,
    },
    {
        "id": "cardio_hiit",
        "name": {"en": "Cardio / HIIT", "vi": "Cardio / HIIT"},
        "default_met": 7.3,
        "met": {"light": 4.8, "moderate": 7.3, "hard": 7.5},
        "apple_health_type": "highIntensityIntervalTraining",
        "is_custom": False,
    },
    {
        "id": "yoga_stretching",
        "name": {"en": "Yoga / Stretching", "vi": "Yoga / Giãn cơ"},
        "default_met": 2.3,
        "met": {"light": 2.3, "moderate": 4.0, "hard": 8.0},
        "apple_health_type": "yoga",
        "is_custom": False,
    },
    {
        "id": "swimming",
        "name": {"en": "Swimming", "vi": "Bơi lội"},
        "default_met": 6.0,
        "met": {"light": 5.8, "moderate": 6.0, "hard": 8.0},
        "apple_health_type": "swimming",
        "is_custom": False,
    },
    {
        "id": "badminton",
        "name": {"en": "Badminton", "vi": "Cầu lông"},
        "default_met": 5.5,
        "met": {"light": 5.5, "moderate": 7.0, "hard": 9.0},
        "apple_health_type": "badminton",
        "is_custom": False,
    },
    {
        "id": "football",
        "name": {"en": "Football", "vi": "Bóng đá"},
        "default_met": 7.0,
        "met": {"light": 3.5, "moderate": 7.0, "hard": 9.5},
        "apple_health_type": "soccer",
        "is_custom": False,
    },
    {
        "id": "volleyball",
        "name": {"en": "Volleyball", "vi": "Bóng chuyền"},
        "default_met": 4.0,
        "met": {"light": 3.0, "moderate": 4.0, "hard": 6.0},
        "apple_health_type": "volleyball",
        "is_custom": False,
    },
]

_BY_ID = {item["id"]: item for item in _ACTIVITIES}


def get_all_activities() -> list[dict[str, Any]]:
    return deepcopy(_ACTIVITIES)


def get_activity(activity_id: str | None) -> dict[str, Any] | None:
    if not activity_id:
        return None
    item = _BY_ID.get(activity_id)
    return deepcopy(item) if item else None


def get_met(activity_id: str | None, intensity: str) -> float | None:
    item = _BY_ID.get(activity_id or "")
    if not item:
        return None
    value = item["met"].get(intensity)
    return float(value) if value is not None else None
