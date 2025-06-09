# Meal Macros Persistence Fix

## Issue Identified

After updating meal macros via `POST /v1/meals/{meal_id}/macros`, when retrieving the meal with `GET /v1/meals/{meal_id}`, the updated weight and nutrition values were not persisted - the meal showed the original data.

## Root Cause

The macro update endpoint was calculating and returning updated values in the response, but **not actually saving the changes to the meal record** in the database.

## Solution Implemented

### 1. **Added Meal Update Method**
Enhanced `MealHandler` with `update_meal_weight()` method that:
- Retrieves the existing meal
- Calculates scaling ratios
- Creates updated meal with new weight information
- **Persists the changes to the database**

```python
def update_meal_weight(self, meal_id: str, weight_grams: float) -> Optional[Meal]:
    """Update meal with new weight and recalculate nutrition."""
    # Get existing meal
    meal = self.meal_repository.find_by_id(meal_id)
    
    # Calculate original weight and create updated meal
    updated_meal = Meal(...)
    
    # Store weight metadata
    setattr(updated_meal, 'updated_weight_grams', weight_grams)
    setattr(updated_meal, 'original_weight_grams', original_weight)
    
    # PERSIST THE CHANGES
    self.meal_repository.save(updated_meal)
    
    return updated_meal
```

### 2. **Updated Macro Endpoint**
Modified `POST /v1/meals/{meal_id}/macros` to:
- Call `meal_handler.update_meal_weight()` to persist changes
- Return updated meal data with proper timestamps
- Set meal status to "analyzing" for background LLM recalculation

### 3. **Enhanced Meal Retrieval**
Updated `DetailedMealResponse.from_domain()` to:
- Detect meals with updated weight information
- Scale nutrition values based on weight changes
- Return consistent per-100g and total nutrition data

```python
# Check if meal has been updated with new weight
if hasattr(meal, 'updated_weight_grams'):
    estimated_weight = meal.updated_weight_grams
    
    # Scale nutrition values
    ratio = meal.updated_weight_grams / meal.original_weight_grams
    total_calories = meal.nutrition.calories * ratio
    total_macros = scale_macros(macros_response, ratio)
```

## Verification Flow

### Before Fix:
1. `POST /v1/meals/{meal_id}/macros` → Returns updated values ✅
2. `GET /v1/meals/{meal_id}` → Returns original values ❌

### After Fix:
1. `POST /v1/meals/{meal_id}/macros` → Returns updated values ✅ + Persists to DB ✅
2. `GET /v1/meals/{meal_id}` → Returns updated values ✅

## Testing

Run the persistence test to verify the fix:

```bash
python test_meal_persistence.py
```

This test:
1. Gets initial meal data
2. Updates weight to 400g
3. Retrieves meal and verifies the weight was persisted
4. Verifies nutrition values were correctly scaled
5. Tests a second update to ensure consistency

## Key Changes Made

### Files Modified:
- `app/handlers/meal_handler.py` - Added `update_meal_weight()` method
- `api/v1/routes/meals.py` - Updated endpoint to use handler method
- `api/schemas/meal_schemas.py` - Enhanced `from_domain()` to handle updated meals

### Data Flow:
1. **API Request** → Update macros with weight
2. **Handler** → Persist weight change to database
3. **Background Task** → Schedule LLM recalculation
4. **API Response** → Return calculated nutrition data
5. **Future Retrieval** → Return persisted updated values

## Benefits

✅ **Persistence**: Meal updates are now permanently saved  
✅ **Consistency**: GET after POST returns the same updated data  
✅ **Accuracy**: Nutrition values are correctly scaled and stored  
✅ **Reliability**: Multiple updates work consistently  
✅ **Traceability**: Original and updated weights are tracked 