"""Request schema for visual body-fat range selections."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from src.domain.model.user.body_fat_visual import (
    BODY_FAT_VISUAL_RANGE_CATALOG_VERSION,
    BODY_FAT_VISUAL_SCHEMA_VERSION,
    is_valid_visual_range_for_sex,
)


class BodyFatVisualProfileRequest(BaseModel):
    """A versioned visual estimate, distinct from measured body-fat percentage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[BODY_FAT_VISUAL_SCHEMA_VERSION]
    range_catalog_version: Literal[BODY_FAT_VISUAL_RANGE_CATALOG_VERSION]
    sex_at_selection: Literal["male", "female"]
    start_range_id: str | None = None
    current_range_id: str
    target_range_id: str | None = None

    @model_validator(mode="after")
    def validate_range_sex(self) -> "BodyFatVisualProfileRequest":
        """Reject catalog identifiers that do not belong to the selected sex."""
        for field_name in ("start_range_id", "current_range_id", "target_range_id"):
            range_id = getattr(self, field_name)
            if range_id is None:
                continue
            if not is_valid_visual_range_for_sex(self.sex_at_selection, range_id):
                raise ValueError(
                    f"{field_name} must be a {self.sex_at_selection} body-fat range"
                )
        return self
