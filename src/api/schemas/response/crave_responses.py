from pydantic import BaseModel


class CraveCard(BaseModel):
    id: str
    meal_name: str
    english_name: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    image_url: str | None = None
    thumbnail_url: str | None = None
    match: int
    reason: str
    locked: bool = False


class CraveDeckResponse(BaseModel):
    meal_type: str
    target_calories: int
    meals: list[CraveCard]
