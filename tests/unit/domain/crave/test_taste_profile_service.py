from src.domain.services.crave.taste_profile_service import (
    SwipeSignal,
    TasteProfileService,
)


def test_save_increases_cuisine_affinity_more_than_skip():
    service = TasteProfileService()
    profile = {"cuisine_affinity": {}, "ingredient_affinity": {}, "tag_affinity": {}}

    after_save = service.apply(
        profile,
        SwipeSignal(
            direction="save",
            cuisine="japanese",
            tags=["high_protein"],
            ingredients=["salmon"],
        ),
    )
    after_skip = service.apply(
        after_save, SwipeSignal(direction="skip", cuisine="italian")
    )

    assert after_save["cuisine_affinity"]["japanese"] > 0
    assert (
        after_skip["cuisine_affinity"].get("italian", 0)
        < after_save["cuisine_affinity"]["japanese"]
    )


def test_cook_weighted_more_than_save():
    service = TasteProfileService()

    p_save = service.apply(
        {"cuisine_affinity": {}, "ingredient_affinity": {}, "tag_affinity": {}},
        SwipeSignal(direction="save", cuisine="thai"),
    )
    p_cook = service.apply(
        {"cuisine_affinity": {}, "ingredient_affinity": {}, "tag_affinity": {}},
        SwipeSignal(direction="cook", cuisine="thai"),
    )

    assert p_cook["cuisine_affinity"]["thai"] > p_save["cuisine_affinity"]["thai"]
