import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes.v1.macros import router as macros_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.tdee import router as tdee_router
from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.daily_meals import router as daily_meals_router
from src.api.routes.v1.user_onboarding import router as user_onboarding_router
from src.api.routes.v2.daily_meals import router as daily_meals_v2_router

load_dotenv()

app = FastAPI(
    title="MealTrack API",
    description="API for meal tracking, nutritional analysis with AI vision capabilities, and smart meal planning",
    version="0.2.0",
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
            "macros": "/v1/macros",
            "tdee": "/v1/tdee",
            "meal_planning": {
                "start_conversation": "/v1/meal-plans/conversations/start",
                "send_message": "/v1/meal-plans/conversations/{conversation_id}/messages",
                "generate_plan": "/v1/meal-plans/generate",
                "get_plan": "/v1/meal-plans/{plan_id}",
                "replace_meal": "/v1/meal-plans/{plan_id}/meals/replace"
            },
            "daily_meal_suggestions": {
                "get_suggestions": "/v1/daily-meals/suggestions",
                "get_single_meal": "/v1/daily-meals/suggestions/{meal_type}"
            },
            "user_onboarding": {
                "save_data": "/v1/user-onboarding/save",
                "get_summary": "/v1/user-onboarding/summary/{user_id}",
                "recalculate_tdee": "/v1/user-onboarding/calculate-tdee/{user_id}"
            },
            "daily_meals_v2": {
                "get_suggestions_by_profile": "/v2/daily-meals/suggestions/{user_profile_id}",
                "get_single_meal_by_profile": "/v2/daily-meals/suggestions/{user_profile_id}/{meal_type}",
                "get_meal_planning_data": "/v2/daily-meals/profile/{user_profile_id}/summary"
            }
        }
    }

app.include_router(meals_router, prefix="/v1")
app.include_router(macros_router, prefix="/v1")
app.include_router(activities_router, prefix="/v1")
app.include_router(tdee_router, prefix="/v1")
app.include_router(meal_plans_router)
app.include_router(daily_meals_router)
app.include_router(user_onboarding_router)
app.include_router(daily_meals_v2_router)

# Serve static files from uploads directory (development)
if os.environ.get('ENVIRONMENT') == 'development':
    uploads_path = os.getenv("UPLOADS_DIR", "./uploads")  # Default to './uploads' if UPLOADS_DIR is not set
    if os.path.exists(uploads_path):
        app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 