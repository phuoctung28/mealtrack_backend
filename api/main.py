from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from api.v1.routes.meals import router as meals_router  # Temporarily commented out
from api.v1.routes.food import router as food_router
from api.v1.routes.ingredients import router as ingredients_router
from api.v1.routes.activities import router as activities_router
from api.v1.routes.macros import router as macros_router
from api.v1.routes.onboarding import router as onboarding_router
from api.v1.routes.food_database import router as food_database_router

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title="MealTrack API",
    description="API for meal tracking and nutritional analysis with AI vision capabilities",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint that returns API information."""
    return {
        "name": "MealTrack API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "available_endpoints": {
            "onboarding": "/v1/onboarding/sections",
            "activities": "/v1/activities",
            "meals": "/v1/meals",
            "food": "/v1/food",
            "ingredients": "/v1/food/{food_id}/ingredients",
            "macros": "/v1/macros",
            "food_database": "/v1/food-database"
        }
    }

# Include API routers
app.include_router(onboarding_router, prefix="/v1")
app.include_router(activities_router, prefix="/v1")
# app.include_router(meals_router, prefix="/v1")  # Temporarily commented out
app.include_router(food_router, prefix="/v1")
app.include_router(ingredients_router, prefix="/v1")
app.include_router(macros_router, prefix="/v1")
app.include_router(food_database_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 