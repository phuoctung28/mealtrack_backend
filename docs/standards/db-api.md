# Database & API Conventions

## Database (SQLAlchemy)
- **Model Naming**: `DBMeal`, `DBNutrition` (Prefix with DB).
- **Primary Keys**: UUID strings (`id = Column(String(36), primary_key=True)`).
- **Timestamps**: Always include `created_at` and `updated_at`.
- **Unit of Work**: Use the UoW pattern via `AsyncSession`.

## API (FastAPI)
- **Versioning**: All routes under `/v1/`.
- **Schemas**: Separate `Request` and `Response` Pydantic models.
- **Mappers**: Use explicit mappers to convert between Domain entities and API Schemas.
- **REST**: Follow standard HTTP methods (GET, POST, PUT, DELETE).

---

## Meal Suggestions API (Phase 06, Phase 01 Multilingual)

### Endpoints

| Method | Endpoint | Purpose | Phase |
|--------|----------|---------|-------|
| POST | `/v1/meal-suggestions` | Generate 3 initial meal suggestions | 06 |
| POST | `/v1/meal-suggestions/regenerate` | Regenerate 3 new suggestions | 06 |
| GET | `/v1/meal-suggestions/{session_id}` | Get session suggestions | 06 |
| POST | `/v1/meal-suggestions/{suggestion_id}/accept` | Accept suggestion with multiplier | 06 |
| POST | `/v1/meal-suggestions/{suggestion_id}/reject` | Reject suggestion with feedback | 06 |
| POST | `/v1/meal-suggestions/{session_id}/discard` | End session | 06 |

### MealSuggestionRequest Schema

```python
class MealSuggestionRequest(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    meal_portion_type: Optional[MealPortionTypeEnum] = None  # snack, main, omad
    meal_size: Optional[MealSizeEnum] = None  # DEPRECATED: use meal_portion_type
    ingredients: List[str]  # Max 20 items
    cooking_time_minutes: CookingTimeEnum  # 20/30/45/60
    dietary_preferences: List[str] = []  # Optional: vegetarian, vegan, etc.
    calorie_target: Optional[int] = None
    exclude_ids: List[str] = []  # For regeneration
    language: str = "en"  # ISO 639-1: en, vi, es, fr, de, ja, zh
```

### Language Support (Phase 01)

- **Supported Languages**: English (en), Vietnamese (vi), Spanish (es), French (fr), German (de), Japanese (ja), Mandarin (zh)
- **Default**: English (en)
- **Validation**: Invalid codes fallback to 'en' with warning
- **Field Location**: `language` parameter in `MealSuggestionRequest`
- **Scope**: Meal names, descriptions, and cooking instructions

### SuggestionSession Model

```python
@dataclass
class SuggestionSession:
    id: str
    user_id: str
    meal_type: str
    meal_portion_type: str  # snack, main, omad
    target_calories: int
    ingredients: List[str]
    cooking_time_minutes: int
    language: str = "en"  # Phase 01: ISO 639-1 language code
    shown_suggestion_ids: List[str]
    dietary_preferences: List[str]
    allergies: List[str]
    created_at: datetime
    expires_at: datetime  # 4-hour TTL
```

### Example Request (with language)

```json
POST /v1/meal-suggestions
{
  "meal_type": "lunch",
  "meal_portion_type": "main",
  "ingredients": ["chicken breast", "broccoli", "rice"],
  "cooking_time_minutes": 30,
  "language": "vi",
  "dietary_preferences": []
}
```

### Response Structure

Session + array of 3 MealSuggestion objects with multilingual content (names, descriptions, instructions in requested language).
