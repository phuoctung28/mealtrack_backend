# TDEE Calculation Implementation - Flutter Compatible

## Overview

This implementation provides a complete TDEE (Total Daily Energy Expenditure) calculation API endpoint that perfectly matches your Flutter `OnboardingData` structure and returns results in the format expected by your Flutter `TdeeResult` class.

## Architecture

The implementation follows the 4-layer Clean Architecture pattern:

### 1. Domain Layer (`domain/`)

**Models** (`domain/model/tdee.py`):
- `TdeeRequest`: Domain entity with unit conversion and validation
- `TdeeResponse`: Matches Flutter `TdeeResult` structure exactly
- `MacroTargets`: Matches Flutter `MacroTargets` structure exactly
- `Sex`, `ActivityLevel`, `Goal`, `UnitSystem`: Enums matching Flutter

**Services** (`domain/services/tdee_service.py`):
- `TdeeCalculationService`: Core business logic for BMR and TDEE calculations
- Implements Mifflin-St Jeor formula (when body fat % absent)
- Implements Katch-McArdle formula (when body fat % present)
- Calculates macro distributions for maintenance/cutting/bulking goals

### 2. Application Layer (`app/`)

**Handlers** (`app/handlers/tdee_handler.py`):
- `TdeeHandler`: Orchestrates domain services and handles API-to-domain translation
- Converts API strings to domain enums
- Handles unit system conversion

### 3. Infrastructure Layer (`infra/`)

No additional infrastructure components needed for this stateless calculation service.

### 4. Presentation Layer (`api/`)

**Schemas** (`api/schemas/tdee_schemas.py`):
- `TdeeCalculationRequest`: Perfectly matches Flutter `OnboardingData`
- `TdeeCalculationResponse`: Perfectly matches Flutter `TdeeResult`
- `MacroTargetsResponse`: Perfectly matches Flutter `MacroTargets`

**Routes** (`api/routes/v1/tdee.py`):
- `POST /v1/tdee`: HTTP endpoint with unit system support

## Flutter Compatibility

The implementation exactly matches your Flutter data structures:

### Request Format (matches OnboardingData)
```json
{
  "age": 30,
  "sex": "male", 
  "height": 180,          // In user's preferred units
  "weight": 80,           // In user's preferred units
  "body_fat_percentage": 15,
  "activity_level": "active",  // sedentary|light|moderate|active|extra
  "goal": "bulking",           // maintenance|cutting|bulking
  "unit_system": "metric"      // metric|imperial
}
```

### Response Format (matches TdeeResult)
```json
{
  "bmr": 1838.8,
  "tdee": 3171.9,
  "maintenance": {
    "calories": 3171.9,
    "protein": 141.1,
    "fat": 88.1,
    "carbs": 453.6
  },
  "cutting": {
    "calories": 2537.5,
    "protein": 141.1,
    "fat": 56.4,
    "carbs": 366.4
  },
  "bulking": {
    "calories": 3647.7,
    "protein": 141.1,
    "fat": 101.3,
    "carbs": 542.8
  }
}
```

## Unit System Support

### Metric System
- Height: 100-272 cm
- Weight: 30-250 kg

### Imperial System  
- Height: 39-107 inches
- Weight: 66-551 lbs

The backend automatically converts imperial units to metric for calculations and returns results in universal units (calories, grams).

## Enum Compatibility

### Activity Levels (matches Flutter ActivityLevel)
- `sedentary` → 1.2x multiplier
- `light` → 1.375x multiplier  
- `moderate` → 1.55x multiplier
- `active` → 1.725x multiplier (changed from 'very' to match Flutter)
- `extra` → 1.9x multiplier

### Goals (matches Flutter Goal)
- `maintenance` → TDEE × 1.0
- `cutting` → TDEE × 0.8 (20% deficit)
- `bulking` → TDEE × 1.15 (15% surplus)

### Sex (matches Flutter Sex)
- `male`
- `female`

## Calculation Logic

### BMR Calculation
- **With body fat %**: Katch-McArdle formula: `370 + 21.6 × lean_mass_kg`
- **Without body fat %**: Mifflin-St Jeor formula:
  - Male: `10 × weight + 6.25 × height - 5 × age + 5`
  - Female: `10 × weight + 6.25 × height - 5 × age - 161`

### TDEE Calculation
BMR × Activity multiplier (converted from imperial if needed)

### Macro Distribution
- **Protein**: 0.8g per lb body weight (consistent across goals)
- **Fat**: 20% of calories (cutting), 25% (maintenance/bulking)
- **Carbs**: Remaining calories ÷ 4

## Validation

### Input Validation
- Age: 13-120 years
- Height: Unit-specific ranges (metric vs imperial)
- Weight: Unit-specific ranges (metric vs imperial)
- Body fat: 5-55% (when provided)
- All enum values match Flutter exactly

### Business Rules
- Unit conversion handled automatically
- Type safety with enums
- Comprehensive error handling

## Usage Examples

### Metric Units with Body Fat
```bash
curl -X POST "http://localhost:8000/v1/tdee" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "sex": "male",
    "height": 180,
    "weight": 80,
    "body_fat_percentage": 15,
    "activity_level": "active",
    "goal": "bulking",
    "unit_system": "metric"
  }'
```

### Imperial Units without Body Fat
```bash
curl -X POST "http://localhost:8000/v1/tdee" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 25,
    "sex": "female", 
    "height": 65,
    "weight": 130,
    "body_fat_percentage": null,
    "activity_level": "light",
    "goal": "cutting",
    "unit_system": "imperial"
  }'
```

## Testing

Comprehensive test suite (`tests/test_tdee_endpoint.py`):
- ✅ Tests both metric and imperial units
- ✅ Validates all Flutter enum values  
- ✅ Tests unit conversion validation
- ✅ Verifies response format matches Flutter exactly
- ✅ Tests both BMR formulas (with/without body fat)

## Integration with Flutter

Your Flutter app can now send the `OnboardingData` directly to the backend:

```dart
// In your Flutter app
final response = await http.post(
  Uri.parse('$baseUrl/v1/tdee'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'age': onboardingData.age,
    'sex': onboardingData.sex?.name,
    'height': onboardingData.height,
    'weight': onboardingData.weight,
    'body_fat_percentage': onboardingData.bodyFatPercentage,
    'activity_level': onboardingData.activityLevel?.name,
    'goal': onboardingData.goal?.name,
    'unit_system': onboardingData.unitSystem.name,
  }),
);

final tdeeResult = TdeeResult.fromJson(jsonDecode(response.body));
```

The backend response maps perfectly to your Flutter `TdeeResult` class without any transformation needed! 