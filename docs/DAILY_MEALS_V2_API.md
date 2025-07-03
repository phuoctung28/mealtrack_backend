# Daily Meal Suggestions V2 API Documentation

## Overview

The V2 API provides meal suggestions based on `user_profile_id` instead of requiring all user data to be passed in the request. It automatically fetches user information from the database including:

- Profile data (age, gender, height, weight)
- User preferences (dietary restrictions, health conditions, allergies)
- Fitness goals (activity level, target weight)
- TDEE calculations (BMR, calories, macros)

## Endpoints

### 1. Get Daily Meal Suggestions by Profile

```
POST /v2/daily-meals/suggestions/{user_profile_id}
```

Generates 3-5 meal suggestions for a full day based on the user's profile.

#### Path Parameters
- `user_profile_id`: The unique identifier of the user profile

#### Response
```json
{
  "date": "2024-01-15",
  "meal_count": 4,
  "meals": [
    {
      "meal_id": "uuid",
      "meal_type": "breakfast",
      "name": "High-Protein Vegetarian Omelette",
      "description": "Protein-packed omelette with vegetables",
      "prep_time": 10,
      "cook_time": 15,
      "total_time": 25,
      "calories": 450,
      "protein": 28.5,
      "carbs": 32.0,
      "fat": 22.0,
      "ingredients": ["3 eggs", "spinach", "mushrooms", "cheese"],
      "instructions": ["Beat eggs", "Cook vegetables", "Make omelette"],
      "is_vegetarian": true,
      "is_vegan": false,
      "is_gluten_free": true,
      "cuisine_type": "International"
    }
  ],
  "daily_totals": {
    "calories": 2400.0,
    "protein": 120.0,
    "carbs": 300.0,
    "fat": 80.0
  },
  "target_totals": {
    "calories": 2500.0,
    "protein": 125.0,
    "carbs": 312.0,
    "fat": 83.0
  }
}
```

### 2. Get Single Meal Suggestion by Profile

```
POST /v2/daily-meals/suggestions/{user_profile_id}/{meal_type}
```

Generates a single meal suggestion for a specific meal type.

#### Path Parameters
- `user_profile_id`: The unique identifier of the user profile
- `meal_type`: One of `breakfast`, `lunch`, `dinner`, `snack`

#### Response
```json
{
  "meal": {
    "meal_id": "uuid",
    "meal_type": "lunch",
    "name": "Mediterranean Quinoa Bowl",
    "description": "Nutritious quinoa bowl with Mediterranean flavors",
    // ... same structure as meal object above
  }
}
```

### 3. Get Meal Planning Data Summary

```
GET /v2/daily-meals/profile/{user_profile_id}/summary
```

Returns all the data that would be used for meal planning. Useful for debugging and verification.

#### Response
```json
{
  "profile": {
    "id": "profile-uuid",
    "user_id": "user-uuid",
    "age": 28,
    "gender": "male",
    "height_cm": 175.0,
    "weight_kg": 75.0,
    "body_fat_percentage": 15.0,
    "is_current": true
  },
  "goal": {
    "id": "goal-uuid",
    "activity_level": "moderate",
    "fitness_goal": "maintenance",
    "target_weight_kg": 75.0,
    "meals_per_day": 3,
    "snacks_per_day": 2,
    "is_current": true
  },
  "preferences": {
    "dietary": ["vegetarian", "high_protein"],
    "health_conditions": [],
    "allergies": ["nuts"]
  },
  "latest_tdee": {
    "id": "tdee-uuid",
    "calculation_date": "2024-01-15",
    "bmr": 1750.0,
    "tdee": 2500.0,
    "target_calories": 2500.0,
    "macros": {
      "protein": 125.0,
      "carbs": 312.0,
      "fat": 83.0
    }
  }
}
```

## How It Works

1. **Profile Lookup**: The API fetches the user profile using the provided ID
2. **Data Gathering**: 
   - Gets current user goal (activity level, fitness goal)
   - Gets user preferences (dietary, health conditions, allergies)
   - Gets latest TDEE calculation or calculates new one
3. **Meal Generation**: Uses AI to generate meals that:
   - Match the calorie and macro targets
   - Respect dietary preferences
   - Avoid allergens
   - Consider health conditions
4. **Response**: Returns meals with detailed nutritional information

## Benefits Over V1 API

1. **Simpler Integration**: Only need to pass `user_profile_id`
2. **Automatic Updates**: Always uses latest user data
3. **Consistency**: Ensures same data is used across all meal suggestions
4. **Less Network Traffic**: No need to send full user data with each request
5. **Data Validation**: Database ensures data integrity

## Usage Example

```python
import requests

# Assuming you have a user_profile_id from onboarding
profile_id = "550e8400-e29b-41d4-a716-446655440000"

# Get daily meal suggestions
response = requests.post(
    f"http://localhost:8000/v2/daily-meals/suggestions/{profile_id}"
)

if response.status_code == 200:
    data = response.json()
    print(f"Generated {data['meal_count']} meals")
    for meal in data['meals']:
        print(f"{meal['meal_type']}: {meal['name']} ({meal['calories']} cal)")
```

## Error Handling

### 404 Not Found
- User profile not found
- User goal not found

### 500 Internal Server Error
- AI service failure
- Database connection issues

## Testing

Run the test script to see the API in action:

```bash
python test_daily_meals_v2.py
```

This will:
1. Create a test user with profile data
2. Get meal suggestions using the profile ID
3. Show how different profiles get different meal suggestions

## Migration from V1

If you're currently using V1 endpoints, here's how to migrate:

### V1 (Old Way)
```python
# Need to pass all data
user_data = {
    "age": 28,
    "gender": "male",
    "height": 175,
    "weight": 75,
    "activity_level": "moderately_active",
    "goal": "build_muscle",
    "dietary_preferences": ["vegetarian"],
    "health_conditions": [],
    "target_calories": 2800,
    "target_macros": {
        "protein": 140,
        "carbs": 350,
        "fat": 93
    }
}

response = requests.post(
    "http://localhost:8000/v1/daily-meals/suggestions",
    json=user_data
)
```

### V2 (New Way)
```python
# Just pass profile ID
response = requests.post(
    f"http://localhost:8000/v2/daily-meals/suggestions/{profile_id}"
)
```

## Notes

- Profile must exist in database (created during onboarding)
- TDEE is automatically calculated if not already stored
- Uses the most recent (current) profile and goal data
- Respects all dietary preferences and allergies stored in the database