from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.routes.macros import router as macros_router
from api.v1.routes.meals import router as meals_router
from api.v1.routes.activities import router as activities_router

load_dotenv()

app = FastAPI(
    title="MealTrack API",
    description="API for meal tracking and nutritional analysis with AI vision capabilities",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {
        "name": "MealTrack API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "available_endpoints": {
            "onboarding": "/v1/onboarding/sections",
            "activities": "/v1/activities",
            "meals": "/v1/meals",
            "meal_photo_analysis": "/v1/meals/photo",
            "meal_management": "/v1/meals/{meal_id}",
            "meal_search": "/v1/meals/search",
            "meal_macros": "/v1/meals/{meal_id}/macros",
            "ingredients": "/v1/meals/{meal_id}/ingredients",
            "macros": "/v1/macros"
        }
    }

app.include_router(meals_router, prefix="/v1")
app.include_router(macros_router, prefix="/v1")
app.include_router(activities_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 