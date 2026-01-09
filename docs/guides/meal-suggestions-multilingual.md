# Multilingual Meal Suggestions (Phase 01)

Developer guide for implementing and maintaining language support in meal suggestions.

## Overview

Meal suggestion generation supports 7 ISO 639-1 language codes. The language parameter flows through the entire CQRS pipeline and is persisted with the suggestion session.

## Supported Languages

| Code | Language | Usage |
|------|----------|-------|
| en | English | Default |
| vi | Vietnamese | Common in Asia-Pacific |
| es | Spanish | Global reach |
| fr | French | European market |
| de | German | European market |
| ja | Japanese | Asia-specific |
| zh | Mandarin Chinese | Large Asia market |

## Implementation Details

### 1. API Schema Validation (`MealSuggestionRequest`)

Located: `src/api/schemas/request/meal_suggestion_requests.py`

```python
@field_validator("language")
@classmethod
def validate_language_code(cls, v: str) -> str:
    """Validate language code and fallback to 'en' if invalid."""
    valid_languages = {"en", "vi", "es", "fr", "de", "ja", "zh"}
    normalized = v.lower().strip()
    if normalized not in valid_languages:
        warnings.warn(
            f"Unsupported language code '{v}', falling back to 'en'",
            UserWarning,
            stacklevel=2,
        )
        return "en"
    return normalized
```

**Key Points**:
- Normalizes to lowercase
- Validates against whitelist
- Falls back to "en" for invalid codes
- Issues `UserWarning` for debugging

### 2. Command Definition

Located: `src/app/commands/meal_suggestion/generate_meal_suggestions_command.py`

```python
@dataclass
class GenerateMealSuggestionsCommand(Command):
    language: str = "en"  # ISO 639-1 language code
```

### 3. Session Storage

Located: `src/domain/model/meal_suggestion/suggestion_session.py`

```python
@dataclass
class SuggestionSession:
    language: str = "en"  # ISO 639-1 language code (en, vi, es, fr, de, ja, zh)
```

**Persistence**:
- Stored in Redis with 4-hour TTL
- Persists across regeneration requests
- Follows session lifecycle

### 4. Service Integration

Located: `src/domain/services/meal_suggestion/suggestion_orchestration_service.py`

```python
async def generate_suggestions(
    self,
    user_id: str,
    meal_type: str,
    meal_portion_type: str,
    ingredients: List[str],
    cooking_time_minutes: int,
    language: str = "en",
) -> Tuple[SuggestionSession, List[MealSuggestion]]:
    """Generate initial 3 suggestions and create session."""
```

**Service Responsibilities**:
- Accepts validated language parameter
- Stores in `SuggestionSession`
- Passes to meal generation service
- Maintains through session lifetime

## API Usage Examples

### Generate Suggestions in Vietnamese

```bash
curl -X POST http://localhost:8000/v1/meal-suggestions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_type": "lunch",
    "meal_portion_type": "main",
    "ingredients": ["chicken", "rice"],
    "cooking_time_minutes": 30,
    "language": "vi"
  }'
```

### Response Structure

```json
{
  "session": {
    "id": "sess_abc123",
    "language": "vi",
    "meal_type": "lunch",
    "created_at": "2026-01-09T14:45:00Z",
    "expires_at": "2026-01-09T18:45:00Z"
  },
  "suggestions": [
    {
      "id": "meal_1",
      "name": "Gà Nướng cơm",
      "description": "Cơm trắng với gà nướng giúp cung cấp protein cao...",
      "instructions": ["Nướng gà", "Nấu cơm", "Trộn lại"],
      "language": "vi"
    },
    // ... 2 more suggestions
  ]
}
```

## Adding New Languages

To support a new language:

1. **Update whitelist** in `validate_language_code()`
   ```python
   valid_languages = {"en", "vi", "es", "fr", "de", "ja", "zh", "pt"}  # Add "pt"
   ```

2. **Test validation**
   ```python
   # Valid code
   assert validate_language_code("pt") == "pt"

   # Invalid code
   assert validate_language_code("invalid") == "en"
   ```

3. **Update meal generation service** to handle new language in prompts

4. **Document in README.md** and language support table

5. **Add integration tests** for new language

## Testing Language Support

### Unit Tests

```python
def test_language_validation_valid():
    """Valid language codes pass through."""
    request = MealSuggestionRequest(
        meal_type="lunch",
        meal_portion_type=MealPortionTypeEnum.MAIN,
        ingredients=["chicken"],
        cooking_time_minutes=30,
        language="vi",
    )
    assert request.language == "vi"

def test_language_validation_invalid_fallback():
    """Invalid codes fallback to 'en'."""
    request = MealSuggestionRequest(
        meal_type="lunch",
        meal_portion_type=MealPortionTypeEnum.MAIN,
        ingredients=["chicken"],
        cooking_time_minutes=30,
        language="invalid",
    )
    assert request.language == "en"
```

### Integration Tests

```python
async def test_suggestions_in_vietnamese(client, user_token):
    """Suggestions generated in Vietnamese."""
    response = await client.post(
        "/v1/meal-suggestions",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "meal_type": "lunch",
            "meal_portion_type": "main",
            "ingredients": ["chicken"],
            "cooking_time_minutes": 30,
            "language": "vi",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session"]["language"] == "vi"
    assert all(s["language"] == "vi" for s in data["suggestions"])
```

## Backward Compatibility

- **Default**: English ("en")
- **Optional**: Field is not required
- **Safe Fallback**: Invalid codes use English
- **Migration Path**: Clients not sending language get English (no breaking change)

## Performance Considerations

- Language parameter does NOT increase database query complexity
- Stored as string in session (minimal memory overhead)
- No additional API calls for language validation
- Validation happens at request parsing layer (before domain logic)

## Troubleshooting

### Language Not Applied in Response

**Check**:
1. Language code in request matches whitelist
2. Meal generation service uses language parameter
3. Session stores correct language
4. Response mapper includes language in output

### Invalid Language Code Warning

**Expected behavior**: Invalid codes log warning and fallback to "en"

**Example**:
```
UserWarning: Unsupported language code 'pt', falling back to 'en'
```

### Session Language Mismatch

**Cause**: Language changed mid-session (not supported)

**Fix**: Create new session with new language

## Related Docs

- [Meal Suggestions API](../standards/db-api.md#meal-suggestions-api-phase-06-phase-01-multilingual)
- [Data Flow - Multilingual](../architecture/data-flow.md#multilingual-meal-suggestions-phase-01)
- [Project Overview](../project-overview-pdr.md)

## Future Enhancements

- Real-time language switching within session
- Language preference storage in user profile
- Automatic language detection from user locale
- Support for regional variants (e.g., pt-BR, zh-TW)
