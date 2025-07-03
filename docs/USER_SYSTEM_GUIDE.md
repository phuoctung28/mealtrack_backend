# User System Implementation Guide

## Overview

This guide explains how to use the new user system that stores onboarding data and TDEE calculations in a normalized database structure.

## Database Structure

### Core Tables

1. **users** - User authentication and account info
2. **user_profiles** - Physical attributes (with history tracking)
3. **user_preferences** - Dietary preferences and health info
4. **user_goals** - Fitness goals and activity levels (with history)
5. **tdee_calculations** - TDEE calculation history

### Normalized Design Benefits

- **No data redundancy** - Each piece of information stored once
- **Historical tracking** - Track weight, goals, and TDEE changes over time
- **Flexible preferences** - Easy to add/remove dietary preferences
- **Performance** - Optimized indexes for common queries

## Running the Migration

```bash
# Run the migration script
python run_user_migration.py

# Or manually with alembic
alembic upgrade 006
```

## Using the User System

### 1. Save Onboarding Data

```python
from sqlalchemy.orm import Session
from app.services.user_onboarding_service import UserOnboardingService

# In your endpoint
def save_onboarding(db: Session, user_id: str, onboarding_data: dict):
    service = UserOnboardingService(db)
    
    # Onboarding data structure
    data = {
        'personal_info': {
            'age': 30,
            'gender': 'male',
            'height': 175,  # cm
            'weight': 75,   # kg
            'body_fat_percentage': 15  # optional
        },
        'activity_level': {
            'activity_level': 'moderate'  # sedentary/light/moderate/active/extra
        },
        'fitness_goals': {
            'fitness_goal': 'maintenance',  # maintenance/cutting/bulking
            'target_weight': 73  # optional
        },
        'dietary_preferences': {
            'preferences': ['vegetarian', 'gluten_free']
        },
        'health_conditions': {
            'conditions': ['diabetes']
        },
        'allergies': {
            'allergies': ['nuts', 'shellfish']
        },
        'meal_preferences': {
            'meals_per_day': 3,
            'snacks_per_day': 2
        }
    }
    
    result = service.save_onboarding_data(user_id, data)
    return result
```

### 2. Retrieve User Data

```python
from infra.repositories.user_repository import UserRepository

def get_user_data(db: Session, user_id: str):
    repo = UserRepository(db)
    
    # Get current profile
    profile = repo.get_current_user_profile(user_id)
    
    # Get preferences
    preferences = repo.get_user_preferences(user_id)
    
    # Get current goal
    goal = repo.get_current_user_goal(user_id)
    
    # Get latest TDEE calculation
    tdee = repo.get_latest_tdee_calculation(user_id)
    
    return {
        'profile': profile,
        'preferences': preferences,
        'goal': goal,
        'tdee': tdee
    }
```

### 3. Update Daily Meals API

The daily meals API can now use real user data:

```python
@router.post("/suggestions")
async def get_daily_meal_suggestions(
    user_id: str = Header(...),  # Get from auth header
    db: Session = Depends(get_db)
):
    # Get user data from database
    service = UserOnboardingService(db)
    user_data = service.get_user_onboarding_summary(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User data not found")
    
    # Convert to API format
    request_data = {
        'age': user_data['personal_info']['age'],
        'gender': user_data['personal_info']['gender'],
        'height': user_data['personal_info']['height'],
        'weight': user_data['personal_info']['weight'],
        'activity_level': user_data['fitness_info']['activity_level'],
        'goal': user_data['fitness_info']['fitness_goal'],
        'dietary_preferences': user_data['preferences']['dietary'],
        'health_conditions': user_data['preferences']['health_conditions'],
        'target_calories': user_data['latest_calculation']['target_calories'],
        'target_macros': SimpleMacroTargets(
            protein=user_data['latest_calculation']['macros']['protein'],
            carbs=user_data['latest_calculation']['macros']['carbs'],
            fat=user_data['latest_calculation']['macros']['fat']
        )
    }
    
    # Generate suggestions...
```

## Migration Strategy

### Phase 1: Database Setup ✅
- Create all user tables
- Add foreign key columns to existing tables

### Phase 2: User Registration (TODO)
```python
# Create registration endpoint
@router.post("/register")
async def register_user(
    email: str,
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    
    # Hash password (use bcrypt or similar)
    password_hash = hash_password(password)
    
    # Create user
    user = repo.create_user(email, username, password_hash)
    
    return {"user_id": user.id}
```

### Phase 3: Update Existing Data (TODO)
```python
# Migrate hardcoded user_ids to real users
def migrate_existing_data(db: Session):
    # Find all unique user_ids in meal_plans
    user_ids = db.query(MealPlan.user_id).distinct().all()
    
    for (user_id,) in user_ids:
        if user_id == "default_user":
            # Create a default user account
            repo = UserRepository(db)
            user = repo.create_user(
                email="default@example.com",
                username="default_user",
                password_hash="temp_password"
            )
            
            # Update references
            db.query(MealPlan).filter(
                MealPlan.user_id == "default_user"
            ).update({"new_user_id": user.id})
```

### Phase 4: Authentication (TODO)
- Implement JWT or session-based auth
- Add auth middleware to endpoints
- Update endpoints to use authenticated user ID

## Best Practices

### 1. Always Use Current Data
```python
# Good - gets current profile
profile = repo.get_current_user_profile(user_id)

# Bad - might get outdated profile
profile = db.query(UserProfile).filter(
    UserProfile.user_id == user_id
).first()
```

### 2. Track History
```python
# When user updates weight
new_profile = repo.create_user_profile(
    user_id=user_id,
    age=profile.age,
    gender=profile.gender,
    height_cm=profile.height_cm,
    weight_kg=new_weight,  # Updated weight
    body_fat_percentage=profile.body_fat_percentage
)
# This automatically marks old profile as not current
```

### 3. Handle Missing Data
```python
# Always check if user data exists
user_data = service.get_user_onboarding_summary(user_id)
if not user_data:
    # Handle missing data gracefully
    return default_recommendations
```

## API Examples

### Complete Onboarding Flow

```python
# 1. Register user
POST /api/v1/auth/register
{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "secure_password"
}

# 2. Save onboarding data
POST /api/v1/onboarding/complete
Headers: Authorization: Bearer <token>
{
    "personal_info": {...},
    "activity_level": {...},
    // ... all sections
}

# 3. Get personalized meal suggestions
POST /api/v1/daily-meals/suggestions
Headers: Authorization: Bearer <token>
// No body needed - uses stored user data
```

## Database Queries

### Useful Queries

```sql
-- Get user with all current data
SELECT 
    u.id, u.email,
    up.age, up.weight_kg, up.height_cm,
    ug.activity_level, ug.fitness_goal,
    tc.tdee, tc.protein_grams, tc.carbs_grams, tc.fat_grams
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id AND up.is_current = true
LEFT JOIN user_goals ug ON u.id = ug.user_id AND ug.is_current = true
LEFT JOIN tdee_calculations tc ON u.id = tc.user_id
WHERE u.id = ?
ORDER BY tc.calculation_date DESC
LIMIT 1;

-- Track weight history
SELECT weight_kg, created_at 
FROM user_profiles 
WHERE user_id = ?
ORDER BY created_at DESC;

-- Get dietary preferences
SELECT dp.preference
FROM user_dietary_preferences dp
JOIN user_preferences p ON dp.user_preference_id = p.id
WHERE p.user_id = ?;
```

## Next Steps

1. **Create Authentication System**
   - User registration endpoint
   - Login endpoint with JWT tokens
   - Password reset functionality

2. **Update Existing Endpoints**
   - Add authentication middleware
   - Replace hardcoded user_ids with authenticated user
   - Update meal plans and conversations to use real users

3. **Create User Management Endpoints**
   - Update profile endpoint
   - Update preferences endpoint
   - View TDEE history endpoint

4. **Add User Dashboard**
   - Progress tracking
   - Goal achievement metrics
   - Historical data visualization