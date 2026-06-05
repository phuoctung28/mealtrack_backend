"""Projection hint for meal reads.

Controls which related data a meal query eagerly loads. Lives in the domain layer
so application handlers can request a projection without importing infrastructure
(the SQLAlchemy load options for each projection stay in the repositories).
"""

from enum import Enum, auto


class MealProjection(Enum):
    MACROS_ONLY = auto()  # nutrition + food_items only
    FULL = auto()  # image + nutrition + food_items (default)
    FULL_WITH_TRANSLATIONS = auto()  # everything, including translations
