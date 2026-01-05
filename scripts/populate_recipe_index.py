"""
Script to populate Pinecone recipe index using TheMealDB API.
Free alternative to AI generation - fetches real recipes from TheMealDB.

TheMealDB API: https://www.themealdb.com/api.php
- Free tier: 1 request per second
- ~600+ recipes available
- Categories, cuisines, and detailed ingredients

Usage:
    python scripts/populate_recipe_index.py
"""
import asyncio
import json
import logging
import os
import sys
import uuid
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infra.services.pinecone_service import PineconeNutritionService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TheMealDBClient:
    """Client for TheMealDB API."""

    BASE_URL = "https://www.themealdb.com/api/json/v1/1"

    def __init__(self):
        self.session = requests.Session()

    def search_by_category(self, category: str) -> List[Dict]:
        """Get meals by category."""
        try:
            response = self.session.get(f"{self.BASE_URL}/filter.php?c={category}")
            response.raise_for_status()
            data = response.json()
            return data.get("meals", [])
        except Exception as e:
            logger.error(f"Failed to fetch category {category}: {e}")
            return []

    def search_by_area(self, area: str) -> List[Dict]:
        """Get meals by cuisine/area."""
        try:
            response = self.session.get(f"{self.BASE_URL}/filter.php?a={area}")
            response.raise_for_status()
            data = response.json()
            return data.get("meals", [])
        except Exception as e:
            logger.error(f"Failed to fetch area {area}: {e}")
            return []

    def get_meal_details(self, meal_id: str) -> Optional[Dict]:
        """Get full meal details including ingredients and instructions."""
        try:
            time.sleep(0.3)  # Rate limit: ~3 req/sec (being conservative)
            response = self.session.get(f"{self.BASE_URL}/lookup.php?i={meal_id}")
            response.raise_for_status()
            data = response.json()
            meals = data.get("meals", [])
            return meals[0] if meals else None
        except Exception as e:
            logger.error(f"Failed to fetch meal {meal_id}: {e}")
            return None

    def list_categories(self) -> List[str]:
        """List all available categories."""
        try:
            response = self.session.get(f"{self.BASE_URL}/categories.php")
            response.raise_for_status()
            data = response.json()
            return [cat["strCategory"] for cat in data.get("categories", [])]
        except Exception as e:
            logger.error(f"Failed to fetch categories: {e}")
            return []

    def list_areas(self) -> List[str]:
        """List all available cuisines/areas."""
        try:
            response = self.session.get(f"{self.BASE_URL}/list.php?a=list")
            response.raise_for_status()
            data = response.json()
            return [area["strArea"] for area in data.get("meals", [])]
        except Exception as e:
            logger.error(f"Failed to fetch areas: {e}")
            return []


class RecipeIndexPopulator:
    """Populates Pinecone with recipes from TheMealDB."""

    # Meal type mapping from categories
    MEAL_TYPE_MAPPING = {
        "Breakfast": "breakfast",
        "Dessert": "snack",
        "Starter": "snack",
        "Side": "snack",
        "Beef": "dinner",
        "Chicken": "dinner",
        "Lamb": "dinner",
        "Pork": "dinner",
        "Seafood": "dinner",
        "Pasta": "dinner",
        "Vegetarian": "lunch",
        "Vegan": "lunch",
    }

    def __init__(self):
        """Initialize services."""
        self.mealdb = TheMealDBClient()
        self.pinecone = PineconeNutritionService()
        # Skip nutrition enrichment during population - use simple estimation
        self.nutrition_enrichment = None

        # Initialize embedding model for local embedding generation
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Embedding model loaded")

        # Create index if it doesn't exist
        from pinecone import ServerlessSpec

        index_name = "recipes"
        dimension = 384  # all-MiniLM-L6-v2 produces 384-dim embeddings
        existing_indexes = [idx['name'] for idx in self.pinecone.pc.list_indexes()]

        if index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index '{index_name}' (dimension={dimension})...")
            self.pinecone.pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            logger.info(f"✅ Created index '{index_name}'")
            # Wait for index to be ready
            import time
            time.sleep(10)
        else:
            logger.info(f"Index '{index_name}' already exists")

        self.recipes_index = self.pinecone.pc.Index(index_name)
        logger.info("Connected to Pinecone recipes index")

    async def populate_index(self):
        """Fetch recipes from TheMealDB and index in Pinecone."""
        total_recipes = 0
        vectors_batch = []
        processed_ids = set()

        # Get all categories and areas
        logger.info("Fetching categories and cuisines from TheMealDB...")
        categories = self.mealdb.list_categories()
        areas = self.mealdb.list_areas()

        logger.info(f"Found {len(categories)} categories: {categories}")
        logger.info(f"Found {len(areas)} cuisines: {areas}")

        # Fetch meals by category
        logger.info("\n=== Fetching meals by category ===")
        for category in categories:
            logger.info(f"Fetching {category} meals...")
            meals = self.mealdb.search_by_category(category)

            for meal_summary in meals[:20]:  # Limit per category
                meal_id = meal_summary.get("idMeal")
                if meal_id in processed_ids:
                    continue

                meal = self.mealdb.get_meal_details(meal_id)
                if not meal:
                    continue

                vector = self._meal_to_vector(meal, category)
                if vector:
                    vectors_batch.append(vector)
                    processed_ids.add(meal_id)
                    total_recipes += 1

                    # Batch upsert every 100 vectors
                    if len(vectors_batch) >= 100:
                        self._upsert_batch(vectors_batch)
                        vectors_batch = []

        # Fetch meals by area/cuisine
        logger.info("\n=== Fetching meals by cuisine ===")
        for area in areas:
            logger.info(f"Fetching {area} meals...")
            meals = self.mealdb.search_by_area(area)

            for meal_summary in meals[:15]:  # Limit per area
                meal_id = meal_summary.get("idMeal")
                if meal_id in processed_ids:
                    continue

                meal = self.mealdb.get_meal_details(meal_id)
                if not meal:
                    continue

                category = meal.get("strCategory", "Other")
                vector = self._meal_to_vector(meal, category)
                if vector:
                    vectors_batch.append(vector)
                    processed_ids.add(meal_id)
                    total_recipes += 1

                    # Batch upsert every 100 vectors
                    if len(vectors_batch) >= 100:
                        self._upsert_batch(vectors_batch)
                        vectors_batch = []

        # Final batch
        if vectors_batch:
            self._upsert_batch(vectors_batch)

        logger.info(f"\n✅ Recipe index population complete! Total: {total_recipes} recipes")

    def _meal_to_vector(self, meal: Dict, category: str) -> Optional[tuple]:
        """Convert TheMealDB meal to Pinecone vector format."""
        try:
            recipe_id = f"mealdb_{meal.get('idMeal', uuid.uuid4().hex[:12])}"
            name = meal.get("strMeal", "Unknown")
            description = meal.get("strInstructions", "")[:200]  # First 200 chars
            cuisine = meal.get("strArea", "Unknown")

            # Extract ingredients and measurements
            ingredients = []
            for i in range(1, 21):  # TheMealDB has up to 20 ingredients
                ingredient = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")

                if ingredient:
                    ingredient = str(ingredient).strip()
                    measure = str(measure).strip() if measure else ""

                    if ingredient and ingredient.lower() not in ["", "null", "none"]:
                        # Parse measure to get amount and unit
                        amount, unit = self._parse_measure(measure)
                        ingredients.append({
                            "name": ingredient.lower(),
                            "amount": amount,
                            "unit": unit
                        })

            if not ingredients:
                logger.warning(f"Skipping {name} - no ingredients")
                return None

            # Calculate nutrition using simple estimation (fast, no Pinecone calls)
            total_calories = 0.0
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0

            for ing in ingredients:
                try:
                    amount = float(ing["amount"])
                    name_lower = ing["name"].lower()

                    # Simple category-based estimation
                    if any(w in name_lower for w in ["oil", "butter", "cream"]):
                        cal = amount * 9; p = cal * 0.01 / 4; c = cal * 0.01 / 4; f = cal * 0.98 / 9
                    elif any(w in name_lower for w in ["meat", "chicken", "fish", "beef", "pork"]):
                        cal = amount * 1.5; p = cal * 0.50 / 4; c = 0; f = cal * 0.50 / 9
                    elif any(w in name_lower for w in ["rice", "pasta", "bread"]):
                        cal = amount * 3.5; p = cal * 0.12 / 4; c = cal * 0.75 / 4; f = cal * 0.03 / 9
                    elif any(w in name_lower for w in ["cheese", "milk"]):
                        cal = amount * 2.5; p = cal * 0.25 / 4; c = cal * 0.15 / 4; f = cal * 0.55 / 9
                    else:
                        cal = amount * 0.5; p = cal * 0.15 / 4; c = cal * 0.70 / 4; f = cal * 0.05 / 9

                    total_calories += cal
                    total_protein += p
                    total_carbs += c
                    total_fat += f

                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid ingredient: {ing}, error: {e}")
                    continue

            # Determine meal type from category
            meal_type = self.MEAL_TYPE_MAPPING.get(category, "dinner")

            # Detect dietary tags
            dietary_tags = []
            tags = meal.get("strTags") or ""
            if category == "Vegetarian" or "Vegetarian" in tags:
                dietary_tags.append("vegetarian")
            if category == "Vegan" or "Vegan" in tags:
                dietary_tags.extend(["vegan", "vegetarian"])

            # Estimate cooking times (TheMealDB doesn't provide)
            estimated_time = 30  # Default 30 minutes

            # Parse instructions into steps
            instructions = meal.get("strInstructions", "")
            recipe_steps = []
            for i, step_text in enumerate(instructions.split("\r\n"), 1):
                if step_text.strip():
                    recipe_steps.append({
                        "step": i,
                        "instruction": step_text.strip(),
                        "duration_minutes": estimated_time // max(len(recipe_steps) + 1, 3)
                    })

            # Build embedding text
            ingredients_text = " ".join([ing["name"] for ing in ingredients[:5]])
            dietary_text = " ".join(dietary_tags)
            embedding_text = f"{name} | {description} | {cuisine} | {dietary_text} | {ingredients_text}"

            # Metadata
            metadata = {
                "recipe_id": recipe_id,
                "name": name,
                "description": description,
                "meal_type": meal_type,
                "cuisine_type": cuisine.lower(),
                "calories": int(total_calories),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1),
                "prep_time_minutes": 10,
                "cook_time_minutes": 20,
                "total_time_minutes": estimated_time,
                "dietary_tags": dietary_tags,
                "allergens": [],  # Not provided by TheMealDB
                "difficulty": "medium",
                "ingredients": json.dumps(ingredients),
                "recipe_steps": json.dumps(recipe_steps),
                "seasonings": json.dumps([]),
                "source": "themealdb",
                "source_id": meal.get("idMeal"),
                "created_at": datetime.utcnow().isoformat(),
                "quality_score": 0.90,  # TheMealDB recipes are generally high quality
                "youtube": meal.get("strYoutube", ""),
                "image": meal.get("strMealThumb", "")
            }

            logger.debug(
                f"Created recipe vector: {name} | {int(total_calories)} cal | {cuisine}"
            )

            return (recipe_id, embedding_text, metadata)

        except Exception as e:
            logger.error(f"Failed to convert meal {meal.get('strMeal')}: {e}", exc_info=True)
            return None

    def _parse_measure(self, measure: str) -> tuple:
        """Parse measurement string to amount and unit."""
        if not measure or measure.lower() in ["", "null", "to taste"]:
            return (100, "g")

        measure = measure.lower().strip()

        # Common patterns
        import re

        # Try to extract number
        number_match = re.search(r'(\d+\.?\d*)', measure)
        amount = float(number_match.group(1)) if number_match else 100

        # Determine unit
        if "cup" in measure:
            unit = "cup"
        elif "tbsp" in measure or "tablespoon" in measure:
            unit = "tbsp"
        elif "tsp" in measure or "teaspoon" in measure:
            unit = "tsp"
        elif "oz" in measure or "ounce" in measure:
            unit = "oz"
        elif "lb" in measure or "pound" in measure:
            unit = "lb"
        elif "ml" in measure or "millilitre" in measure:
            unit = "ml"
            amount = amount / 240 * 100  # Convert to g equivalent
            unit = "g"
        elif "g" in measure or "gram" in measure:
            unit = "g"
        elif "kg" in measure or "kilogram" in measure:
            unit = "kg"
        else:
            unit = "g"
            amount = 100  # Default

        return (amount, unit)

    def _upsert_batch(self, vectors: List[tuple]):
        """Upsert batch of vectors to Pinecone with local embeddings."""
        try:
            # Generate embeddings for all texts in batch
            texts = [embedding_text for _, embedding_text, _ in vectors]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)

            # Format for Pinecone: list of dicts with id, values (embedding), and metadata
            formatted_vectors = []
            for i, (recipe_id, embedding_text, metadata) in enumerate(vectors):
                formatted_vectors.append({
                    "id": recipe_id,
                    "values": embeddings[i].tolist(),  # Convert numpy array to list
                    "metadata": metadata
                })

            self.recipes_index.upsert(vectors=formatted_vectors)
            logger.info(f"✅ Upserted batch of {len(vectors)} recipes")
        except Exception as e:
            logger.error(f"❌ Upsert failed: {e}", exc_info=True)


async def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("Recipe Index Population Script (TheMealDB)")
    logger.info("=" * 60)
    logger.info("Using TheMealDB API - Free, no AI costs!")
    logger.info("")

    populator = RecipeIndexPopulator()

    try:
        await populator.populate_index()
        logger.info("=" * 60)
        logger.info("✅ SUCCESS: Recipe index populated from TheMealDB")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
