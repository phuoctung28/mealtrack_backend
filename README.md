# MealTrack Backend

A FastAPI-based backend service for meal tracking and nutritional analysis with AI vision capabilities and cloud storage integration.

## Features

- **Image Upload & Storage**: Upload meal images with automatic Cloudinary integration
- **AI-Powered Analysis**: Automatic nutritional analysis using OpenAI's GPT-4 Vision
- **Background Processing**: Asynchronous meal analysis using FastAPI background tasks
- **RESTful API**: Clean REST endpoints for meal management
- **Database Support**: MySQL
- **Clean Architecture**: 4-layer architecture with clear separation of concerns

## Architecture

The application follows an n-layer (Clean Architecture) pattern:

- **Presentation Layer (`src/api/`)**: HTTP endpoints, routers, and request/response handling
- **Application Layer (`src/app/`)**: Use cases, handlers, and application services
- **Domain Layer (`src/domain/`)**: Core business logic, entities, and domain services
- **Infrastructure Layer (`src/infra/`)**: External services, repositories, database, and adapters

## API Endpoints

### Meals
- `POST /v1/meals/image` - Upload a meal image for analysis
- `GET /v1/meals/{meal_id}` - Get complete meal details
- `GET /v1/meals/{meal_id}/status` - Get meal processing status

### Health
- `GET /health` - Health check endpoint
- `GET /` - API information

## Setup and Installation

### Prerequisites
- Python 3.10+
- pip or pipenv

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Environment Configuration

2. Update `.env` with your actual configuration:

**Required Variables:**
- `OPENAI_API_KEY`: Your OpenAI API key for GPT-4 Vision
- `CLOUDINARY_CLOUD_NAME`: Your Cloudinary cloud name
- `CLOUDINARY_API_KEY`: Your Cloudinary API key  
- `CLOUDINARY_API_SECRET`: Your Cloudinary API secret

**Optional Variables:**
- `USE_MOCK_STORAGE=0`: Use Cloudinary (set to 1 for local storage)

### Database Setup

For MySQL setup, update the database environment variables in `.env`.

## Running the Application

### Development Server
```bash
uvicorn src.api.main:app --reload
```

### Production Server
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Swagger Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## Usage Example

### Upload a Meal Image
```bash
curl -X POST "http://localhost:8000/v1/meals/image" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@path/to/your/meal_image.jpg"
```

Response:
```json
{
  "meal_id": "uuid-string",
  "status": "PROCESSING"
}
```

### Check Meal Status
```bash
curl "http://localhost:8000/v1/meals/{meal_id}/status"
```

### Get Complete Meal Details
```bash
curl "http://localhost:8000/v1/meals/{meal_id}"
```

## Background Processing

The application automatically processes uploaded meal images in the background:

1. **PROCESSING**: Image uploaded and stored
2. **ANALYZING**: AI analyzing the image for nutritional content
3. **ENRICHING**: Finalizing nutritional data
4. **READY**: Analysis complete, nutrition data available
5. **FAILED**: Processing failed (check error_message)
