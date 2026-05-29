from src.domain.services.crave.crave_ranking_service import (
    CraveRankingService,
    RankInputs,
)


class Meal:
    def __init__(self, meal_id, calories, cuisine, tags):
        self.id = meal_id
        self.calories = calories
        self.cuisine = cuisine
        self.tags = tags
        self.protein_g = 30
        self.carbs_g = 40
        self.fat_g = 15


def test_budget_fit_prefers_meal_closest_to_target():
    meals = [Meal("a", 520, "japanese", []), Meal("b", 800, "japanese", [])]

    ranked = CraveRankingService().rank(
        meals,
        RankInputs(
            target_calories=540,
            cuisine_affinity={},
            ingredient_affinity={},
            tag_affinity={},
            taste_cosine={},
        ),
    )

    assert ranked[0].meal.id == "a"
    assert 0 <= ranked[0].match <= 100
    assert ranked[0].match > ranked[1].match


def test_reason_reflects_top_factor():
    ranked = CraveRankingService().rank(
        [Meal("a", 540, "japanese", ["high_protein"])],
        RankInputs(
            target_calories=540,
            cuisine_affinity={"japanese": 0.9},
            ingredient_affinity={},
            tag_affinity={},
            taste_cosine={"a": 0.9},
        ),
    )

    assert ranked[0].reason
