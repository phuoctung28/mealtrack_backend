"""Response schemas for visual body-fat range selections."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BodyFatVisualSelectionResponse(BaseModel):
    """One immutable visual body-fat selection."""

    schema_version: Literal[1]
    range_catalog_version: Literal[1]
    sex_at_selection: Literal["male", "female"]
    start_range_id: str | None = None
    current_range_id: str
    target_range_id: str | None
    updated_at: datetime


class BodyFatVisualProfileResponse(BaseModel):
    """Latest selection fields plus the append-only selection history."""

    schema_version: Literal[1]
    range_catalog_version: Literal[1]
    sex_at_selection: Literal["male", "female"]
    start_range_id: str | None = None
    current_range_id: str
    target_range_id: str | None = None
    updated_at: datetime
    history: list[BodyFatVisualSelectionResponse]
