from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.routes.meals import router as meals_router

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
        "docs": "/docs"
    }

# Include API routers
app.include_router(meals_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 