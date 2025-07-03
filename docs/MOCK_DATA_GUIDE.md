# Mock Data Guide

This guide explains how to populate your database with realistic test data for development and testing.

## Available Scripts

### 1. `populate_mock_data.py`
Main script that creates comprehensive mock data including:
- 20+ users with realistic profiles
- Various fitness goals (weight loss, muscle gain, maintenance)
- Different dietary preferences (vegetarian, vegan, keto, etc.)
- Health conditions and allergies
- Historical weight and TDEE data
- Meal plans and conversations

### 2. `quick_test_users.py`
Creates 3 specific test users for immediate testing:
- Test User 1: Vegetarian female, maintenance goal
- Test User 2: Male with diabetes, weight loss goal
- Test User 3: Male muscle building with dairy/shellfish allergies

### 3. `view_users.py`
Displays all users in the database with their:
- Profile IDs (needed for API testing)
- Basic information
- Dietary preferences
- Current TDEE calculations

### 4. `reset_database.py`
Removes all user data while keeping schema intact.

## Usage

### Step 1: Populate Mock Data

```bash
# Create comprehensive test data
python scripts/populate_mock_data.py

# Or create just 3 quick test users
python scripts/quick_test_users.py
```

### Step 2: View Created Users

```bash
# See all users and their profile IDs
python scripts/view_users.py
```

### Step 3: Test the API

Use the profile IDs from step 2 to test the API:

```bash
# Replace {profile_id} with actual ID from view_users.py
curl -X POST http://localhost:8000/v2/daily-meals/suggestions/{profile_id}
```

## Mock Data Details

### User Profiles Include:

1. **Active Young Male** (25yo, 180cm, 75kg)
   - Goal: Muscle building
   - Activity: Active
   - Diet: High protein

2. **Sedentary Office Worker** (35yo female, 165cm, 70kg)
   - Goal: Weight loss
   - Activity: Sedentary
   - Diet: Low carb, gluten-free
   - Health: Diabetes

3. **Fitness Enthusiast** (28yo male, 175cm, 80kg)
   - Goal: Maintenance
   - Activity: Extra active
   - Diet: Vegetarian, high protein
   - Allergies: Shellfish, peanuts

4. **Weight Loss Journey** (42yo female, 160cm, 85kg)
   - Goal: Weight loss
   - Activity: Light
   - Diet: Dairy-free, low carb
   - Health: Hypertension, high cholesterol

5. **Vegan Athlete** (30yo male, 185cm, 82kg)
   - Goal: Muscle building
   - Activity: Extra active
   - Diet: Vegan, high protein, gluten-free

And 15+ more varied profiles...

### Historical Data

Each user gets:
- 3-5 historical weight measurements
- Corresponding TDEE calculations
- Shows realistic weight progression over time

## Testing Different Scenarios

### Test Vegetarian Meals
```bash
# Find a vegetarian user from view_users.py
# Look for users with "vegetarian" in dietary preferences
```

### Test Weight Loss Plans
```bash
# Find users with "cutting" fitness goal
# Their meals will be lower calorie
```

### Test Allergy Handling
```bash
# Find users with allergies (nuts, dairy, shellfish, etc.)
# Verify generated meals avoid these ingredients
```

## Example API Testing Flow

1. **Get Profile Summary**
```bash
curl http://localhost:8000/v2/daily-meals/profile/{profile_id}/summary
```

2. **Get Daily Meal Suggestions**
```bash
curl -X POST http://localhost:8000/v2/daily-meals/suggestions/{profile_id}
```

3. **Get Single Meal**
```bash
curl -X POST http://localhost:8000/v2/daily-meals/suggestions/{profile_id}/breakfast
```

## Resetting Data

If you need to start fresh:

```bash
# WARNING: This deletes all user data!
python scripts/reset_database.py

# Then repopulate
python scripts/populate_mock_data.py
```

## Tips

1. **Profile IDs**: Always use `view_users.py` to get current profile IDs
2. **Variety**: The mock data includes diverse profiles to test edge cases
3. **Realistic Data**: TDEE calculations use actual formulas
4. **Historical Tracking**: Test progress tracking features with historical data

## Common Test Cases

### Low Calorie (Weight Loss)
- Look for users with "cutting" goal
- Should get meals totaling 1500-2000 calories

### High Calorie (Muscle Gain)
- Look for users with "bulking" goal
- Should get meals totaling 2800-3500 calories

### Special Diets
- Vegetarian/Vegan users
- Keto (low carb, high fat)
- Gluten-free users

### Multiple Restrictions
- Users with both dietary preferences AND allergies
- Should respect all restrictions