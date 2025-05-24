#!/bin/bash

# This script helps set up environment variables for MealTrack backend

if [ ! -f .env ]; then
  echo "Creating .env file from template"
  echo "# API Configuration" > .env
  echo "API_KEY=dev_key_$(date +%s)" >> .env
  echo "" >> .env
  echo "# Storage Configuration" >> .env
  echo "USE_MOCK_STORAGE=1  # Set to 0 to use Cloudinary" >> .env
  echo "" >> .env
  echo "# OpenAI Configuration" >> .env
  echo "OPENAI_API_KEY=your_openai_key_here" >> .env
  echo "" >> .env
  echo "# Cloudinary Configuration" >> .env
  echo "CLOUDINARY_CLOUD_NAME=your_cloud_name" >> .env
  echo "CLOUDINARY_API_KEY=your_api_key" >> .env
  echo "CLOUDINARY_API_SECRET=your_api_secret" >> .env
  
  echo ".env file created successfully!"
  echo "Please edit the .env file to set your API keys and configuration."
else
  echo ".env file already exists."
fi

# Make the uploads directory if it doesn't exist
if [ ! -d uploads ]; then
  echo "Creating uploads directory for local storage"
  mkdir -p uploads
  echo "uploads directory created."
else
  echo "uploads directory already exists."
fi

echo ""
echo "Environment setup completed."
echo "Run 'uvicorn api.main:app --reload' to start the development server." 