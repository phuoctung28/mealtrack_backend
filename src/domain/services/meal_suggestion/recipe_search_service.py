"""
Service for searching recipes in Pinecone index.
Enables fast meal suggestion retrieval via semantic search.
"""
import json
import logging
from typing import List, Optional
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
from src.infra.services.pinecone_service import PineconeNutritionService

logger = logging.getLogger(__name__)


@dataclass
class RecipeSearchCriteria:
    """Search criteria for recipe lookup."""
    meal_type: str
    target_calories: int
    calorie_tolerance: int = 100  # ±100 cal
    max_cook_time: Optional[int] = None
    dietary_preferences: List[str] = None
    allergies: List[str] = None
    ingredients: List[str] = None
    exclude_ids: List[str] = None

    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.dietary_preferences is None:
            self.dietary_preferences = []
        if self.allergies is None:
            self.allergies = []
        if self.ingredients is None:
            self.ingredients = []
        if self.exclude_ids is None:
            self.exclude_ids = []


@dataclass
class RecipeSearchResult:
    """Recipe retrieved from Pinecone."""
    recipe_id: str
    name: str
    description: str
    ingredients: List[dict]
    recipe_steps: List[dict]
    seasonings: List[str]
    macros: dict
    prep_time_minutes: int
    confidence_score: float


class RecipeSearchService:
    """Searches Pinecone recipe index for meal suggestions."""

    def __init__(self, pinecone_service: PineconeNutritionService = None):
        """Initialize with optional Pinecone service."""
        self._pinecone = pinecone_service
        if not self._pinecone:
            try:
                self._pinecone = PineconeNutritionService()
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone service: {e}")
                self._pinecone = None

        # Load embedding model for query encoding
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded embedding model for recipe search")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None

        self.recipes_index = None
        if self._pinecone:
            try:
                self.recipes_index = self._pinecone.pc.Index("recipes")
                logger.info("Connected to Pinecone recipes index")
            except Exception as e:
                logger.warning(f"Recipes index not available: {e}")

    def search_recipes(
        self,
        criteria: RecipeSearchCriteria,
        top_k: int = 10
    ) -> List[RecipeSearchResult]:
        """
        Search for recipes matching criteria.

        Args:
            criteria: Search criteria
            top_k: Number of results to return

        Returns:
            List of matching recipes, sorted by relevance
        """
        if not self.recipes_index or not self.embedding_model:
            logger.warning("Recipes index or embedding model not available, returning empty results")
            return []

        # Build search query text
        query_parts = [criteria.meal_type]

        if criteria.ingredients:
            query_parts.extend(criteria.ingredients[:5])

        if criteria.dietary_preferences:
            query_parts.extend(criteria.dietary_preferences)

        query_text = " ".join(query_parts)

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query_text).tolist()

        # Build metadata filters
        filters = {
            "meal_type": {"$eq": criteria.meal_type},
            "calories": {
                "$gte": criteria.target_calories - criteria.calorie_tolerance,
                "$lte": criteria.target_calories + criteria.calorie_tolerance
            }
        }

        if criteria.max_cook_time:
            filters["total_time_minutes"] = {"$lte": criteria.max_cook_time}

        if criteria.exclude_ids:
            filters["recipe_id"] = {"$nin": criteria.exclude_ids}

        try:
            # Search Pinecone with generated embedding
            logger.debug(
                f"Searching recipes: meal_type={criteria.meal_type}, "
                f"calories={criteria.target_calories}±{criteria.calorie_tolerance}, "
                f"query='{query_text}'"
            )

            results = self.recipes_index.query(
                vector=query_embedding,  # Use locally generated embedding
                top_k=top_k,
                include_metadata=True,
                filter=filters
            )

            # Convert to domain objects
            recipes = []
            matches = results.get("matches", [])

            logger.info(f"Pinecone returned {len(matches)} recipe matches")

            for match in matches:
                metadata = match.get("metadata", {})

                # Parse JSON fields
                try:
                    ingredients = json.loads(metadata.get("ingredients", "[]"))
                    recipe_steps = json.loads(metadata.get("recipe_steps", "[]"))
                    seasonings = json.loads(metadata.get("seasonings", "[]"))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse recipe metadata: {e}")
                    continue

                recipes.append(
                    RecipeSearchResult(
                        recipe_id=metadata.get("recipe_id", ""),
                        name=metadata.get("name", ""),
                        description=metadata.get("description", ""),
                        ingredients=ingredients,
                        recipe_steps=recipe_steps,
                        seasonings=seasonings,
                        macros={
                            "calories": metadata.get("calories", 0),
                            "protein": metadata.get("protein", 0),
                            "carbs": metadata.get("carbs", 0),
                            "fat": metadata.get("fat", 0)
                        },
                        prep_time_minutes=metadata.get("total_time_minutes", 20),
                        confidence_score=match.get("score", 0.5)
                    )
                )

            logger.info(
                f"Recipe search returned {len(recipes)} valid results "
                f"(avg confidence: {sum(r.confidence_score for r in recipes) / len(recipes):.2f})"
                if recipes else "Recipe search returned 0 results"
            )
            return recipes

        except Exception as e:
            logger.error(f"Recipe search failed: {e}", exc_info=True)
            return []
