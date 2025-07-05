"""
Meal domain events.
"""
from src.app.events.meal.meal_analysis_completed_event import MealAnalysisCompletedEvent
from src.app.events.meal.meal_analysis_started_event import MealAnalysisStartedEvent
from src.app.events.meal.meal_enrichment_completed_event import MealEnrichmentCompletedEvent
from src.app.events.meal.meal_enrichment_started_event import MealEnrichmentStartedEvent
from src.app.events.meal.meal_image_uploaded_event import MealImageUploadedEvent
from src.app.events.meal.meal_nutrition_updated_event import MealNutritionUpdatedEvent

__all__ = [
    "MealImageUploadedEvent",
    "MealAnalysisStartedEvent",
    "MealAnalysisCompletedEvent",
    "MealNutritionUpdatedEvent",
    "MealEnrichmentStartedEvent",
    "MealEnrichmentCompletedEvent",
]