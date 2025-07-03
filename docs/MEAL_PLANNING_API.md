# Meal Planning API Documentation

## Overview

The Smart Meal Planner Assistant helps users create customized meal plans through a conversational interface or direct API calls. It uses Google's Gemini AI to generate personalized meal suggestions that adapt to different dietary preferences, fitness goals, and cooking constraints.

## API Endpoints

### Conversational Meal Planning

#### Start a Conversation

```
POST /v1/meal-plans/conversations/start?user_id={user_id}
```

Starts a new meal planning conversation with the assistant.

**Response:**
```json
{
  "conversation_id": "uuid",
  "state": "asking_dietary_preferences",
  "assistant_message": "Hi there! 👋 I'd be happy to help you plan your meals..."
}
```

#### Send Message

```
POST /v1/meal-plans/conversations/{conversation_id}/messages
```

**Request Body:**
```json
{
  "message": "I'm gluten-free and prefer vegetarian meals"
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "state": "asking_allergies",
  "assistant_message": "Got it – gluten-free and vegetarian. 👍 Next, do you have any food allergies?",
  "requires_input": true,
  "meal_plan_id": null
}
```

#### Get Conversation History

```
GET /v1/meal-plans/conversations/{conversation_id}
```

Returns the full conversation history including all messages and context.

### Direct Meal Plan Generation

#### Generate Meal Plan

```
POST /v1/meal-plans/generate?user_id={user_id}
```

Generate a meal plan directly without conversation.

**Request Body:**
```json
{
  "preferences": {
    "dietary_preferences": ["vegetarian", "gluten_free"],
    "allergies": ["nuts"],
    "fitness_goal": "muscle_gain",
    "meals_per_day": 3,
    "snacks_per_day": 2,
    "cooking_time_weekday": 30,
    "cooking_time_weekend": 60,
    "favorite_cuisines": ["Italian", "Mexican"],
    "disliked_ingredients": ["tofu"],
    "plan_duration": "weekly"
  }
}
```

**Response:**
```json
{
  "plan_id": "uuid",
  "user_id": "user_123",
  "preferences": {...},
  "days": [
    {
      "date": "2024-01-15",
      "meals": [
        {
          "meal_id": "uuid",
          "meal_type": "breakfast",
          "name": "Greek Yogurt Parfait",
          "description": "A quick high-protein breakfast",
          "prep_time": 5,
          "cook_time": 0,
          "total_time": 5,
          "calories": 350,
          "protein": 25.5,
          "carbs": 35.2,
          "fat": 12.3,
          "ingredients": ["Greek yogurt", "Mixed berries", "Granola", "Honey"],
          "instructions": ["Layer yogurt in bowl", "Add berries", "Top with granola"],
          "is_vegetarian": true,
          "is_vegan": false,
          "is_gluten_free": false,
          "cuisine_type": null
        }
      ],
      "total_nutrition": {
        "calories": 2150,
        "protein": 125.5,
        "carbs": 230.8,
        "fat": 78.4
      }
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Conversation Flow

The assistant guides users through these steps:

1. **Dietary Preferences** - vegan, vegetarian, gluten-free, keto, etc.
2. **Allergies** - nuts, dairy, shellfish, etc.
3. **Fitness Goals** - weight loss, muscle gain, maintenance, general health
4. **Meal Count** - number of meals and snacks per day
5. **Plan Duration** - daily or weekly meal plan
6. **Cooking Time** - available time on weekdays and weekends
7. **Cuisine Preferences** - favorite cuisines and disliked ingredients
8. **Confirmation** - review and confirm preferences
9. **Plan Generation** - AI generates personalized meal plan

## Dietary Preferences

Supported dietary preferences:
- `vegan`
- `vegetarian`
- `pescatarian`
- `gluten_free`
- `keto`
- `paleo`
- `low_carb`
- `dairy_free`
- `none`

## Fitness Goals

Supported fitness goals:
- `weight_loss` - Lower calorie, balanced meals
- `muscle_gain` - High protein meals (30-40g per meal)
- `maintenance` - Balanced macros
- `general_health` - Varied, nutritious meals

## Example Conversation

```
User: Hello, I need help planning my meals for the week.