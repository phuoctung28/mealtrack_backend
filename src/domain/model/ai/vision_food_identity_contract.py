"""Vision output contract for food identity and portion only."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.model.nutrition import MAX_FOOD_ITEM_QUANTITY


def _strip_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    return stripped


class VisionFoodIdentity(BaseModel):
    """Single food identity extracted from an image without nutrition values."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    preparation: str | None = Field(None, max_length=120)
    estimated_grams: float = Field(..., gt=0, le=MAX_FOOD_ITEM_QUANTITY)
    grams_min: float | None = Field(None, gt=0, le=MAX_FOOD_ITEM_QUANTITY)
    grams_max: float | None = Field(None, gt=0, le=MAX_FOOD_ITEM_QUANTITY)
    confidence: float = Field(0.5, ge=0, le=1)

    @field_validator("name", "preparation")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required_text(value)

    @model_validator(mode="after")
    def validate_gram_range(self) -> "VisionFoodIdentity":
        if (
            self.grams_min is not None
            and self.grams_max is not None
            and self.grams_min > self.grams_max
        ):
            raise ValueError("grams_min must be less than or equal to grams_max")
        return self


class VisionFoodIdentityResponse(BaseModel):
    """Structured image response with food identity and portions only."""

    model_config = ConfigDict(extra="forbid")

    is_food: bool = True
    dish_name: str | None = Field(None, max_length=200)
    emoji: str | None = Field(None, max_length=32)
    foods: list[VisionFoodIdentity] = Field(default_factory=list, max_length=8)
    confidence: float = Field(0.5, ge=0, le=1)

    @field_validator("dish_name")
    @classmethod
    def validate_dish_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required_text(value)

    @model_validator(mode="after")
    def require_foods_for_food_images(self) -> "VisionFoodIdentityResponse":
        if self.is_food and not self.foods:
            raise ValueError("foods must contain at least one item when is_food is true")
        return self
