"""Feature flag queries."""

from src.app.queries.feature_flag.get_feature_flags_query import GetFeatureFlagsQuery
from src.app.queries.feature_flag.get_feature_flag_by_name_query import (
    GetFeatureFlagByNameQuery,
)

__all__ = ["GetFeatureFlagsQuery", "GetFeatureFlagByNameQuery"]
