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

Create a `.env` file in the root directory with the following variables:

**AI & External APIs:**
- `GOOGLE_API_KEY`: Your Google API key (e.g., for Gemini AI vision)
- `USDA_FDC_API_KEY`: USDA FoodData Central API key for nutrition data
- `PINECONE_API_KEY`: Pinecone API key for vector database

**Database:**
- `DB_PASSWORD`: MySQL database password

**Cloud Storage (Cloudinary):**
- `CLOUDINARY_CLOUD_NAME`: Your Cloudinary cloud name
- `CLOUDINARY_API_KEY`: Your Cloudinary API key
- `CLOUDINARY_API_SECRET`: Your Cloudinary API secret
- `UPLOADS_DIR`: Local directory for file uploads
- `USE_MOCK_STORAGE`: Set to `1` for local storage, `0` for Cloudinary (default: `0`)

**Application Settings:**
- `ENVIRONMENT`: Environment mode (e.g., `development`, `production`, `staging`)

**Firebase Authentication:**
- `FIREBASE_CREDENTIALS`: Path to Firebase service account credentials JSON file (recommended for local development)
  - Example: `/path/to/firebase-service-account.json`
  - For development: Use staging Firebase project credentials
  - For production: Use production Firebase project credentials
- `FIREBASE_SERVICE_ACCOUNT_JSON`: Firebase service account credentials as JSON string (recommended for production/cloud deployments)
  - Example: `'{"type":"service_account","project_id":"your-project-id",...}'`
  - Takes precedence over FIREBASE_CREDENTIALS if both are set
  - Useful for cloud platforms where file paths are not ideal

**Email/SMTP Configuration:**
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port
- `SMTP_USERNAME`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP authentication password
- `EMAIL_FROM_ADDRESS`: Email address to send from
- `EMAIL_FROM_NAME`: Display name for sent emails

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