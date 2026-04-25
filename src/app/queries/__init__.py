"""
Query definitions for CQRS pattern.
"""

# Import from activity module
from .activity import (
    GetDailyActivitiesQuery,
)

# Import from meal module
from .meal import (
    GetDailyMacrosQuery,
    GetMealByIdQuery,
)

# Import from tdee module
# No TDEE queries imported - all removed
# Import from user module
from .user import (
    GetUserProfileQuery,
)

__all__ = [
    # Meal queries
    "GetDailyMacrosQuery",
    "GetMealByIdQuery",
    # User queries
    "GetUserProfileQuery",
    # Activity queries
    "GetDailyActivitiesQuery",
]
