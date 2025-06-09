# Macro Endpoints Improvements

## Overview

The macro endpoints have been significantly improved to address the issues with serving information and provide better meal-based tracking with gram estimation.

## Key Issues Addressed

### 1. **Vague Serving Information**
- **Before**: `{"size": 1, "amount": 1, "unit": "string"}` - unclear and inconsistent
- **After**: `{"weight_grams": 250.0}` - precise and measurable

### 2. **Meal-Based Tracking**
- **Before**: Generic macro calculation not linked to specific meals
- **After**: Direct meal ID tracking with portion control

### 3. **Gram-Based Measurements**
- **Before**: Vague units like "bowl", "cup", "piece"
- **After**: Precise weight measurements in grams

## Updated API Structure

### 📊 **Updated Schemas**

#### Meal Macros Update Request
```json
{
  "weight_grams": 250.0  // Required: precise weight in grams
}
```

#### Consumed Macros Request
```json
{
  "meal_id": "meal-123",           // Required: specific meal ID
  "weight_grams": 180.0,           // Optional: actual consumed weight
  "portion_percentage": 75.0       // Optional: percentage consumed
}
```

#### Nutrition Summary Response
```json
{
  "meal_name": "Chicken Stir Fry",
  "total_calories": 420.0,
  "total_weight_grams": 350.0,
  "calories_per_100g": 120.0,
  "macros_per_100g": {
    "protein": 9.5,
    "carbs": 12.8,
    "fat": 5.2,
    "fiber": 2.8
  },
  "total_macros": {
    "protein": 33.3,
    "carbs": 44.8,
    "fat": 18.2,
    "fiber": 9.8
  },
  "confidence_score": 0.92
}
```

### 🛠️ **Updated Endpoints**

#### 1. Update Meal Macros
```
POST /v1/meals/{meal_id}/macros
```
- **Input**: `{"weight_grams": 280.0}`
- **Output**: Complete meal data with scaled nutrition per 100g and total
- **Features**: 
  - Immediate proportional calculation
  - Background LLM recalculation for accuracy
  - Per-100g consistency for easy comparison

#### 2. Track Consumed Macros
```
POST /v1/macros/consumed
```
- **Input**: Meal ID + optional weight/percentage
- **Output**: Daily macro progress with recommendations
- **Features**:
  - Meal-based tracking
  - Flexible portion input (weight or percentage)
  - Real-time daily goal progress

#### 3. Get Meal Macros (New)
```
GET /v1/macros/meal/{meal_id}?weight_grams=200
```
- **Output**: Meal nutrition data, optionally scaled to specific weight
- **Features**:
  - Default meal nutrition information
  - Optional weight-based scaling
  - Consistent per-100g format

## Example Usage Flows

### 🔄 **Flow 1: Upload and Adjust Meal Portion**

1. **Upload meal image**
   ```bash
   POST /v1/meals/image
   # Returns: meal_id
   ```

2. **Get initial nutrition**
   ```bash
   GET /v1/meals/{meal_id}
   # Returns: estimated weight and nutrition
   ```

3. **Adjust to actual weight**
   ```bash
   POST /v1/meals/{meal_id}/macros
   Body: {"weight_grams": 280.0}
   ```

### 🍽️ **Flow 2: Track Meal Consumption**

1. **Get meal macros for planning**
   ```bash
   GET /v1/macros/meal/{meal_id}?weight_grams=200
   ```

2. **Track actual consumption**
   ```bash
   POST /v1/macros/consumed
   Body: {"meal_id": "meal-123", "weight_grams": 180.0}
   ```

3. **Check daily progress**
   ```bash
   GET /v1/macros/daily
   ```

## Benefits

### ✅ **Precision**
- Gram-based measurements eliminate ambiguity
- Per-100g nutrition for consistent comparison
- Accurate portion tracking

### ✅ **Usability**
- Clear, simple API structure
- Flexible portion input methods
- Real-time feedback and recommendations

### ✅ **Meal Integration**
- Direct meal ID linking
- Seamless upload-to-tracking flow
- LLM-enhanced accuracy

### ✅ **Flexibility**
- Multiple portion input methods (weight, percentage)
- Optional parameters for different use cases
- Backward-compatible improvements

## Testing

Run the test script to see the improvements in action:

```bash
python test_improved_macros.py
```

This script demonstrates:
- Gram-based meal macro retrieval
- Portion scaling calculations
- Meal-based consumption tracking
- Daily progress monitoring

## Migration Notes

### Breaking Changes
- `UpdateMealMacrosRequest` now uses `weight_grams` instead of `size`/`amount`/`unit`
- `ConsumedMacrosRequest` now requires `meal_id` and uses optional weight/percentage
- Meal responses use `weight_grams`, `calories_per_100g`, `total_calories` structure

### API Improvements
- Added `/v1/macros/meal/{meal_id}` endpoint for meal-specific nutrition data
- Enhanced portion calculation accuracy
- Improved recommendation system with meal context 