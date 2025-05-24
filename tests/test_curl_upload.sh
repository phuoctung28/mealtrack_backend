#!/bin/bash

# Test script for meal image upload using curl
# This script uploads a test image to the API and checks the response

# Path to test image
TEST_IMAGE="tests/test_data/noodle_soup.jpg"

# API endpoint
API_URL="http://127.0.0.1:8000/v1/meals/image"

# Check if test image exists
if [ ! -f "$TEST_IMAGE" ]; then
    echo "Test image not found at $TEST_IMAGE"
    echo "Downloading test image..."
    python tests/download_test_image.py
    
    if [ ! -f "$TEST_IMAGE" ]; then
        echo "Failed to download test image. Exiting."
        exit 1
    fi
fi

echo "Using test image: $TEST_IMAGE"
echo "Uploading to: $API_URL"

# Upload image with curl
RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@$TEST_IMAGE")

# Check if curl command succeeded
if [ $? -ne 0 ]; then
    echo "Error: curl command failed"
    exit 1
fi

echo "Response: $RESPONSE"

# Extract meal_id from response
MEAL_ID=$(echo $RESPONSE | grep -o '"meal_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$MEAL_ID" ]; then
    echo "Error: Could not extract meal_id from response"
    exit 1
fi

echo "Successfully created meal with ID: $MEAL_ID"

# Check meal status
STATUS_URL="http://127.0.0.1:8000/v1/meals/${MEAL_ID}/status"
echo "Checking status at: $STATUS_URL"

STATUS_RESPONSE=$(curl -s "$STATUS_URL")

echo "Status response: $STATUS_RESPONSE"

# Check meal details
DETAILS_URL="http://127.0.0.1:8000/v1/meals/${MEAL_ID}"
echo "Checking meal details at: $DETAILS_URL"

DETAILS_RESPONSE=$(curl -s "$DETAILS_URL")

echo "Details response: $DETAILS_RESPONSE"

echo "Test completed successfully!"
exit 0 