# Daily Meal Suggestions API Documentation

## Overview

The Daily Meal Suggestions API provides personalized meal recommendations based on user onboarding data. It generates 3-5 meals per day that align with the user's:
- Physical attributes (age, gender, height, weight)
- Activity level and fitness goals
- Dietary preferences and restrictions
- Health conditions
- Calculated nutritional needs

## Endpoints

### 1. Get Daily Meal Suggestions

```
POST /v1/daily-meals/suggestions
```

Generates 3-5 meal suggestions for a full day based on user preferences.

#### Request Body

```json
{
  "age": 28,
  "gender": "male",
  "height": 175,
  "weight": 75,
  "activity_level": "moderately_active",
  "goal": "build_muscle",
  "dietary_preferences": ["vegetarian"],
  "health_conditions": [],
  "target_calories": 2800,  // Optional - will be calculated if not provided
  "target_macros": {        // Optional - will be calculated if not provided
    "protein_grams": 140,
    "carbs_grams": 350,
    "fat_grams": 93
  }
}
```

#### Response

```json
{
  "date": "2024-01-15",
  "meal_count": 4,
  "meals": [
    {
      "meal_id": "uuid",
      "meal_type": "breakfast",
      "name": "Protein-Packed Oatmeal Bowl",
      "description": "High-protein oatmeal with Greek yogurt and nuts",
      "prep_time": 5,
      "cook_time": 10,
      "total_time": 15,
      "calories": 650,
      "protein": 35.5,
      "carbs": 78.2,
      "fat": 18.3,
      "ingredients": [
        "80g rolled oats",
        "150g Greek yogurt",
        "30g almonds",
        "1 banana",
        "1 tbsp honey"
      ],
      "instructions": [
        "Cook oats with water",
        "Mix in Greek yogurt",
        "Top with sliced banana and almonds",
        "Drizzle with honey"
      ],
      "is_vegetarian": true,
      "is_vegan": false,
      "is_gluten_free": false,
      "cuisine_type": "International"
    },
    // ... more meals
  ],
  "daily_totals": {
    "calories": 2785.5,
    "protein": 142.3,
    "carbs": 348.7,
    "fat": 91.2
  },
  "target_totals": {
    "calories": 2800,
    "protein": 140,
    "carbs": 350,
    "fat": 93
  }
}
```

### 2. Get Single Meal Suggestion

```
POST /v1/daily-meals/suggestions/{meal_type}
```

Generates a single meal suggestion for a specific meal type.

#### Path Parameters
- `meal_type`: One of `breakfast`, `lunch`, `dinner`, `snack`

#### Request Body
Same as daily suggestions endpoint

#### Response

```json
{
  "meal": {
    "meal_id": "uuid",
    "meal_type": "lunch",
    "name": "Mediterranean Quinoa Bowl",
    "description": "Protein-rich quinoa with chickpeas and vegetables",
    // ... same structure as meal object above
  }
}
```

## Field Definitions

### Activity Levels
- `sedentary`: Little to no exercise
- `lightly_active`: Light exercise 1-3 days/week
- `moderately_active`: Moderate exercise 3-5 days/week
- `very_active`: Hard exercise 6-7 days/week
- `extra_active`: Very hard exercise & physical job

### Fitness Goals
- `lose_weight`: Create calorie deficit for fat loss
- `maintain_weight`: Maintain current weight
- `gain_weight`: Create calorie surplus
- `build_muscle`: Optimize for muscle growth

### Common Dietary Preferences
- `vegetarian`
- `vegan`
- `gluten_free`
- `dairy_free`
- `keto`
- `paleo`
- `low_carb`

## Integration with Onboarding

This API is designed to work seamlessly with user data collected during onboarding:

1. **Personal Info Section**: Age, gender, height, weight
2. **Activity Level Section**: Exercise frequency and intensity
3. **Fitness Goals Section**: Weight/muscle goals
4. **Dietary Preferences Section**: Restrictions and preferences
5. **Health Conditions Section**: Medical considerations

## Nutritional Calculations

If `target_calories` and `target_macros` are not provided, the API will:
1. Calculate BMR using the Mifflin-St Jeor equation
2. Apply activity factor to get TDEE
3. Adjust calories based on fitness goal
4. Calculate macro distribution based on goal

## Example Usage

```python
import requests

# User data from onboarding
user_data = {
    "age": 30,
    "gender": "female",
    "height": 165,
    "weight": 65,
    "activity_level": "moderately_active",
    "goal": "lose_weight",
    "dietary_preferences": ["gluten_free"],
    "health_conditions": ["diabetes"]
}

# Get daily suggestions
response = requests.post(
    "http://localhost:8000/v1/daily-meals/suggestions",
    json=user_data
)

if response.status_code == 200:
    data = response.json()
    print(f"Generated {data['meal_count']} meals")
    for meal in data['meals']:
        print(f"{meal['meal_type']}: {meal['name']} ({meal['calories']} cal)")
```

## Error Handling

### 400 Bad Request
- Missing required fields
- Invalid field values
- Invalid meal type

### 500 Internal Server Error
- AI service failure
- Calculation errors

## Notes

- Meals are generated using Google's Gemini AI
- Nutritional values are estimates
- Recipes respect all dietary restrictions
- Fallback meals are provided if AI generation fails
- Each request generates fresh suggestions (not cached)