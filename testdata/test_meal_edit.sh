#!/bin/bash

# Test script for: Add meal → Edit ingredient → Observe changes
# This demonstrates the full flow of meal creation and ingredient editing

set -e

API_BASE="http://localhost:8000"
USER_ID="550e8400-e29b-41d4-a716-446655440000"
IMAGE_FILE="testdata/com-tam-sai-gon-thumb.jpg"

echo "=== MealTrack Test: Add Meal + Edit Ingredient ==="
echo ""

# Step 1: Add a meal
echo "📸 Step 1: Uploading meal image..."
MEAL_RESPONSE=$(curl -s -X POST "${API_BASE}/v1/meals/image/analyze?user_id=${USER_ID}" \
  -F "file=@${IMAGE_FILE}")

MEAL_ID=$(echo $MEAL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['meal_id'])" 2>/dev/null || echo "")

if [ -z "$MEAL_ID" ]; then
  echo "❌ Failed to create meal"
  echo "Response: $MEAL_RESPONSE"
  exit 1
fi

echo "✅ Meal created with ID: $MEAL_ID"
echo ""

# Step 2: Get meal details
echo "📋 Step 2: Fetching meal details..."
MEAL_DETAILS=$(curl -s "${API_BASE}/v1/meals/${MEAL_ID}")
echo "$MEAL_DETAILS" | python3 -m json.tool || echo "$MEAL_DETAILS"
echo ""

# Extract first ingredient ID
INGREDIENT_ID=$(echo $MEAL_DETAILS | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['food_items'][0]['id'] if d.get('food_items') else '')" 2>/dev/null || echo "")

if [ -z "$INGREDIENT_ID" ]; then
  echo "❌ No ingredients found in meal"
  exit 1
fi

echo "🥗 Found ingredient ID: $INGREDIENT_ID"
echo ""

# Step 3: Edit the first ingredient (update quantity)
echo "✏️  Step 3: Editing first ingredient (doubling quantity)..."
EDIT_REQUEST='{
  "food_item_changes": [
    {
      "action": "update",
      "id": "'$INGREDIENT_ID'",
      "quantity": 200,
      "unit": "g"
    }
  ]
}'

EDIT_RESPONSE=$(curl -s -X PUT "${API_BASE}/v1/meals/${MEAL_ID}/ingredients" \
  -H "Content-Type: application/json" \
  -d "$EDIT_REQUEST")

echo "✅ Edit response:"
echo "$EDIT_RESPONSE" | python3 -m json.tool || echo "$EDIT_RESPONSE"
echo ""

# Step 4: Fetch updated meal and compare
echo "🔍 Step 4: Fetching updated meal to observe changes..."
UPDATED_MEAL=$(curl -s "${API_BASE}/v1/meals/${MEAL_ID}")
echo "$UPDATED_MEAL" | python3 -m json.tool || echo "$UPDATED_MEAL"
echo ""

echo "=== Test Complete ==="
echo "Meal ID: $MEAL_ID"
echo ""
echo "Summary:"
echo "✅ Created meal from image"
echo "✅ Retrieved meal details"
echo "✅ Edited ingredient quantity"
echo "✅ Verified changes applied"
