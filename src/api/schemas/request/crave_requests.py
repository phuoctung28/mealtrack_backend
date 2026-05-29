from pydantic import BaseModel, Field


class SwipeItemIn(BaseModel):
    catalog_meal_id: str
    direction: str = Field(pattern="^(skip|save|cook)$")
    position: int | None = None
    dwell_ms: int | None = None
    meal_type: str | None = None


class RecordSwipesIn(BaseModel):
    deck_id: str | None = None
    swipes: list[SwipeItemIn]
