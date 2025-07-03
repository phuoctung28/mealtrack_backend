# User Database Schema Design

## Overview

This document describes the normalized database schema for storing user data, profiles, preferences, and TDEE calculations following database normalization principles.

## Database Tables

### 1. users
Core user table for authentication and basic account info.

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### 2. user_profiles
Stores physical attributes and personal info. Can track historical changes.

```sql
CREATE TABLE user_profiles (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id VARCHAR(36) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 13 AND age <= 120),
    gender VARCHAR(20) NOT NULL,  -- male, female, other
    height_cm FLOAT NOT NULL CHECK (height_cm > 0),
    weight_kg FLOAT NOT NULL CHECK (weight_kg > 0),
    body_fat_percentage FLOAT,  -- Optional
    is_current BOOLEAN DEFAULT TRUE,  -- Latest profile record
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_current (user_id, is_current)
);
```

### 3. user_preferences
Stores dietary preferences and health conditions.

```sql
CREATE TABLE user_preferences (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_preference (user_id)
);

CREATE TABLE user_dietary_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_preference_id VARCHAR(36) NOT NULL,
    preference VARCHAR(50) NOT NULL,  -- vegetarian, vegan, gluten_free, etc.
    FOREIGN KEY (user_preference_id) REFERENCES user_preferences(id) ON DELETE CASCADE,
    INDEX idx_preference (user_preference_id)
);

CREATE TABLE user_health_conditions (
    id VARCHAR(36) PRIMARY KEY,
    user_preference_id VARCHAR(36) NOT NULL,
    condition VARCHAR(100) NOT NULL,  -- diabetes, hypertension, etc.
    FOREIGN KEY (user_preference_id) REFERENCES user_preferences(id) ON DELETE CASCADE,
    INDEX idx_condition (user_preference_id)
);

CREATE TABLE user_allergies (
    id VARCHAR(36) PRIMARY KEY,
    user_preference_id VARCHAR(36) NOT NULL,
    allergen VARCHAR(100) NOT NULL,  -- nuts, dairy, shellfish, etc.
    FOREIGN KEY (user_preference_id) REFERENCES user_preferences(id) ON DELETE CASCADE,
    INDEX idx_allergen (user_preference_id)
);
```

### 4. user_goals
Tracks fitness goals and activity levels over time.

```sql
CREATE TABLE user_goals (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id VARCHAR(36) NOT NULL,
    activity_level VARCHAR(30) NOT NULL,  -- sedentary, light, moderate, active, extra
    fitness_goal VARCHAR(30) NOT NULL,  -- maintenance, cutting, bulking
    target_weight_kg FLOAT,  -- Optional target weight
    meals_per_day INTEGER DEFAULT 3,
    snacks_per_day INTEGER DEFAULT 1,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_goal_current (user_id, is_current)
);
```

### 5. tdee_calculations
Stores TDEE calculation history for tracking progress.

```sql
CREATE TABLE tdee_calculations (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id VARCHAR(36) NOT NULL,
    user_profile_id VARCHAR(36) NOT NULL,  -- Links to specific profile snapshot
    user_goal_id VARCHAR(36) NOT NULL,  -- Links to specific goal snapshot
    bmr FLOAT NOT NULL,
    tdee FLOAT NOT NULL,
    target_calories FLOAT NOT NULL,
    -- Macro targets (SimpleMacroTargets)
    protein_grams FLOAT NOT NULL,
    carbs_grams FLOAT NOT NULL,
    fat_grams FLOAT NOT NULL,
    calculation_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_profile_id) REFERENCES user_profiles(id),
    FOREIGN KEY (user_goal_id) REFERENCES user_goals(id),
    INDEX idx_user_date (user_id, calculation_date)
);
```

## Relationships

1. **One-to-Many**:
   - User → UserProfiles (historical tracking)
   - User → UserGoals (historical tracking)
   - User → TdeeCalculations
   - UserPreferences → DietaryPreferences
   - UserPreferences → HealthConditions
   - UserPreferences → Allergies

2. **One-to-One**:
   - User → Current UserProfile (is_current = true)
   - User → Current UserGoal (is_current = true)
   - User → UserPreferences

## Benefits of This Design

1. **Normalization**: 
   - No redundant data
   - Each piece of information stored in one place
   - Easy to update without inconsistencies

2. **Historical Tracking**:
   - Can track weight/measurement changes over time
   - Can track goal changes over time
   - TDEE calculation history for progress tracking

3. **Flexibility**:
   - Easy to add new dietary preferences
   - Easy to add new health conditions
   - Can support multiple goals per user in future

4. **Performance**:
   - Indexed on common queries (user_id, is_current)
   - Separate tables prevent large row sizes
   - Can query current data efficiently

## Migration Strategy

1. Create all tables in order (users first, then dependent tables)
2. Migrate existing hardcoded user_ids to proper user records
3. Update existing meal_plans and conversations to reference real users
4. Add authentication middleware to API endpoints