import json
import logging
import os
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class WeeklyIngredientBasedMealPlanService:
    """
    Generates a Monday-to-Sunday plan with **one** Gemini call.
    We no longer compute real dates – the response just labels the
    days “Monday”, “Tuesday”, … “Sunday”.
    """

    def __init__(self) -> None:
        key = os.getenv("GOOGLE_API_KEY")
        self.llm = (
            ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.2,  # Lower temperature for more consistent output
                max_output_tokens=6000,  # Reduced from 8000 to lower costs
                google_api_key=key,
                response_mime_type="application/json",  # pure-JSON mode
            )
            if key
            else None
        )

    # ─────────────────────────────────────────────────────────────── #
    # public API                                                     #
    # ─────────────────────────────────────────────────────────────── #

    def generate_weekly_meal_plan(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Single entry-point.  If no API key → runtime error."""
        if self.llm is None:
            raise RuntimeError("GOOGLE_API_KEY missing — cannot call Gemini.")

        prompt = self._build_prompt(request)
        raw = self.llm.invoke(
            [
                SystemMessage(
                    content="Meal planner. JSON only, no markdown."
                ),
                HumanMessage(content=prompt),
            ]
        ).content

        data = self._extract_json(raw)  # → {"week":[…]}
        self._validate_response_structure(data, request)
        flat_meals = self._flatten_week(data["week"])
        return self._format_weekly_response(flat_meals, request, request.get("user_id", "unknown"))

    # ─────────────────────────────────────────────────────────────── #
    # helpers                                                        #
    # ─────────────────────────────────────────────────────────────── #

    @staticmethod
    def _build_prompt(req: Dict[str, Any]) -> str:
        ing = ", ".join(req.get("available_ingredients", [])) or "(any)"
        season = ", ".join(req.get("available_seasonings", [])) or "basic spices"
        dietary_prefs = req.get("dietary_preferences", [])
        meals_per_day = req.get("meals_per_day", 3)
        include_snacks = req.get("include_snacks", False)
        target_calories = req.get("target_calories", 2000)
        
        # Define meal types based on configuration
        meal_types = ["breakfast", "lunch", "dinner"]
        if meals_per_day == 4:
            meal_types.append("lunch")  # Add second lunch or brunch
        
        snack_requirement = ""
        if include_snacks:
            meal_types.append("snack")
            snack_requirement = "\n6. Include 1 healthy snack per day."
        
        schema = (
            '{"week":[{"day":"Monday","meals":[{"meal_type":"breakfast","name":"…",'
            '"description":"…","calories":450,"protein":25.0,"carbs":55.0,"fat":15.0,'
            '"prep_time":10,"cook_time":15,"ingredients":["…"],"instructions":["…"],'
            '"is_vegetarian":true,"is_vegan":false,"is_gluten_free":false,"cuisine_type":"International"}]},'
            '{"day":"Tuesday","meals":[]}, "…"]}'
        )

        dietary_requirements = ""
        if dietary_prefs:
            dietary_requirements = f"\nDietary preferences: {', '.join(dietary_prefs)}"

        calorie_guidance = f"\nDaily target: ~{target_calories // 7 * 7} calories total per day"

        return (
            f"Generate a concise 7-day meal plan (Monday-Sunday) using only available ingredients.\n"
            f"Ingredients: {ing}\n"
            f"Seasonings: {season}{dietary_requirements}{calorie_guidance}\n"
            f"Meal types required: {', '.join(meal_types)}\n"
            "Rules:\n"
            "1. Use ONLY listed ingredients - no exceptions.\n"
            "2. Generate exactly 3 main meals per day" + (" + 1 snack" if include_snacks else "") + ".\n"
            "3. Each meal must have: meal_type, name, description, calories, protein, carbs, fat, prep_time, cook_time, ingredients, instructions, is_vegetarian, is_vegan, is_gluten_free, cuisine_type.\n"
            "4. Accurate nutritional values and dietary flags.\n"
            "5. Keep instructions concise (3-5 steps max)." + snack_requirement + "\n"
            f"Output ONLY valid JSON:\n{schema}"
        )

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", text).strip()
        data = json.loads(text)
        if "week" not in data:
            raise ValueError("Missing 'week' key in model output")
        return data

    @staticmethod
    def _validate_response_structure(data: Dict[str, Any], request: Dict[str, Any]) -> None:
        """Validate that the response meets requirements."""
        week_data = data.get("week", [])
        if len(week_data) != 7:
            raise ValueError(f"Expected 7 days, got {len(week_data)}")
        
        required_fields = {"meal_type", "name", "calories", "protein", "carbs", "fat", 
                          "ingredients", "instructions", "is_vegetarian", "is_vegan", 
                          "is_gluten_free", "cuisine_type"}
        
        include_snacks = request.get("include_snacks", False)
        expected_meals_per_day = 3 + (1 if include_snacks else 0)
        
        for day in week_data:
            day_name = day.get("day", "")
            meals = day.get("meals", [])
            
            if len(meals) < expected_meals_per_day:
                logger.warning(f"{day_name}: Expected {expected_meals_per_day} meals, got {len(meals)}")
            
            for meal in meals:
                missing_fields = required_fields - meal.keys()
                if missing_fields:
                    logger.warning(f"{day_name} meal missing fields: {missing_fields}")

    @staticmethod
    def _flatten_week(week_block: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        meals: List[Dict[str, Any]] = []
        for day in week_block:
            for meal in day["meals"]:
                meals.append({"day": day["day"], **meal})
        return meals

    # ─────────────────────────────────────────────────────────────── #
    # original formatter – date logic removed                        #
    # ─────────────────────────────────────────────────────────────── #

    def _format_weekly_response(
        self, meals: List[Dict[str, Any]], req: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        
        # Calculate start and end dates for current week (Monday to Sunday)
        today = datetime.now().date()
        days_since_monday = today.weekday()  # Monday = 0
        start_date = today - timedelta(days=days_since_monday)
        end_date = start_date + timedelta(days=6)
        
        # Ensure all meals have required dietary fields
        for meal in meals:
            meal.setdefault("is_vegetarian", False)
            meal.setdefault("is_vegan", False)
            meal.setdefault("is_gluten_free", False)
            meal.setdefault("cuisine_type", "International")
        
        total_cals = sum(m["calories"] for m in meals)
        total_prot = sum(m["protein"] for m in meals)
        total_carbs = sum(m["carbs"] for m in meals)
        total_fat = sum(m["fat"] for m in meals)

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for m in meals:
            grouped.setdefault(m["day"], []).append(m)

        return {
            "user_id": user_id,
            "plan_type": "weekly",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": grouped,           # Monday-→-Sunday blocks
            "meals": meals,            # flat list
            "total_nutrition": {
                "calories": total_cals,
                "protein": round(total_prot, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1),
            },
            "daily_average_nutrition": {
                "calories": total_cals // 7,
                "protein": round(total_prot / 7, 1),
                "carbs": round(total_carbs / 7, 1),
                "fat": round(total_fat / 7, 1),
            },
            "target_nutrition": {
                "calories": req.get("target_calories", 1800),
                "protein": req.get("target_protein", 120.0),
                "carbs": req.get("target_carbs", 200.0),
                "fat": req.get("target_fat", 80.0),
            },
            "user_preferences": {
                "dietary_preferences": req.get("dietary_preferences", []),
                "health_conditions": req.get("health_conditions", []),
                "allergies": req.get("allergies", []),
                "activity_level": req.get("activity_level", "moderate"),
                "fitness_goal": req.get("fitness_goal", "maintenance"),
                "meals_per_day": req.get("meals_per_day", 3),
                "snacks_per_day": 1 if req.get("include_snacks", False) else 0,
            },
        }
