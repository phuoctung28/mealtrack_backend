# SimpleMacroTargets Documentation

## Overview

The `SimpleMacroTargets` class is a simplified version of macro targets designed specifically for frontend use. It contains only the essential macronutrients: protein, carbs, and fat.

## Class Definition

```python
from pydantic import BaseModel, Field

class SimpleMacroTargets(BaseModel):
    """
    Simplified macro targets class for frontend use.
    Contains only the essential macronutrients: protein, carbs, and fat.
    """
    protein: float = Field(..., description="Protein target in grams", ge=0)
    carbs: float = Field(..., description="Carbohydrates target in grams", ge=0)
    fat: float = Field(..., description="Fat target in grams", ge=0)
```

## Features

### 1. Simplified Structure
- Only contains the three essential macronutrients
- No additional fields like fiber, sugar, or micronutrients
- Easy to serialize and deserialize for API communication

### 2. Automatic Calorie Calculation
```python
@property
def total_calories(self) -> float:
    """Calculate total calories from macros"""
    return (self.protein * 4) + (self.carbs * 4) + (self.fat * 9)
```

### 3. JSON Serialization Support
```python
# Convert to dictionary
macro_dict = macro_targets.to_dict()

# Create from dictionary
macro_targets = SimpleMacroTargets.from_dict(data)
```

## Usage Examples

### In API Requests

```json
{
  "age": 30,
  "gender": "male",
  "height": 175,
  "weight": 75,
  "activity_level": "moderately_active",
  "goal": "build_muscle",
  "dietary_preferences": ["vegetarian"],
  "target_macros": {
    "protein": 150.0,
    "carbs": 300.0,
    "fat": 80.0
  }
}
```

### In API Responses

```json
{
  "target_totals": {
    "calories": 2520.0,
    "protein": 150.0,
    "carbs": 300.0,
    "fat": 80.0
  }
}
```

### Frontend Usage (TypeScript/Dart)

```typescript
interface SimpleMacroTargets {
  protein: number;
  carbs: number;
  fat: number;
}

// Calculate calories
function calculateCalories(macros: SimpleMacroTargets): number {
  return (macros.protein * 4) + (macros.carbs * 4) + (macros.fat * 9);
}
```

## Integration Points

### 1. Daily Meal Suggestions API
- Used in `UserPreferencesRequest` to specify custom macro targets
- Returned in `DailyMealSuggestionsResponse` as target totals

### 2. TDEE Calculation Service
- When TDEE service calculates macros, they're converted to `SimpleMacroTargets`
- Provides seamless integration between calculated and custom targets

### 3. Meal Planning Features
- Used to validate that suggested meals meet macro targets
- Helps distribute macros across multiple meals

## Benefits

1. **Frontend Simplicity**: Only the essential data needed for display
2. **Type Safety**: Pydantic validation ensures all values are valid
3. **Flexibility**: Can be used with both calculated and custom targets
4. **Consistency**: Same structure used throughout the API

## Migration from Complex MacroTargets

If migrating from a more complex macro structure:

```python
# From complex structure
complex_macros = {
    "calories": 2500,
    "protein_grams": 150,
    "carbs_grams": 300,
    "fat_grams": 80,
    "fiber_grams": 30,
    "sugar_grams": 50
}

# To SimpleMacroTargets
simple_macros = SimpleMacroTargets(
    protein=complex_macros["protein_grams"],
    carbs=complex_macros["carbs_grams"],
    fat=complex_macros["fat_grams"]
)
```

## Validation

All fields must be non-negative numbers (>= 0). The Pydantic model automatically validates this constraint.