"""Unit tests for angle-tolerant meal scan visual cache."""

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from PIL import Image

from src.app.services.meal_scan_visual_cache_service import (
    build_identity_key,
    parse_visual_identity,
    score_visual_match,
)
from src.domain.model.meal_scan_visual_identity import (
    MealScanVisualIdentity,
    ParsedVisualIdentity,
)
from src.domain.utils.scene_signature import (
    build_scene_signature,
    ingredient_jaccard,
    scene_cosine_similarity,
)


def _jpeg_bytes(color: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_scene_signature_is_stable_for_same_image():
    data = _jpeg_bytes((180, 120, 60))
    left = build_scene_signature(data)
    right = build_scene_signature(data)
    assert len(left) == 48
    assert scene_cosine_similarity(left, right) > 0.99


def test_scene_signature_differs_for_different_backgrounds():
    warm = build_scene_signature(_jpeg_bytes((200, 150, 80)))
    cool = build_scene_signature(_jpeg_bytes((40, 80, 180)))
    assert scene_cosine_similarity(warm, cool) < 0.9


def test_ingredient_jaccard():
    assert ingredient_jaccard(["rice", "chicken"], ["chicken", "rice"]) == 1.0
    assert ingredient_jaccard(["rice"], ["chicken"]) == 0.0


def test_parse_visual_identity_builds_stable_key():
    parsed = parse_visual_identity(
        {
            "structured_data": {
                "is_food": True,
                "dish_slug": "Chicken Rice Bowl",
                "ingredients": ["Rice", "Chicken", "broccoli"],
                "container": "White Bowl",
                "background": "Wooden Table",
                "confidence": 0.9,
            }
        }
    )
    assert parsed is not None
    assert parsed.dish_slug == "chicken_rice_bowl"
    assert parsed.ingredients == ("broccoli", "chicken", "rice")
    assert parsed.identity_key == build_identity_key(
        dish_slug="chicken_rice_bowl",
        ingredients=["broccoli", "chicken", "rice"],
        container="white_bowl",
        background="wooden_table",
    )


def test_score_visual_match_prefers_same_scene_and_ingredients():
    parsed = ParsedVisualIdentity(
        dish_slug="chicken_rice_bowl",
        ingredients=("broccoli", "chicken", "rice"),
        container="white_bowl",
        background="wooden_table",
        identity_key="k",
        confidence=0.9,
    )
    signature = build_scene_signature(_jpeg_bytes((200, 150, 80)))
    candidate = MealScanVisualIdentity(
        id=str(uuid4()),
        user_id=str(uuid4()),
        meal_id=str(uuid4()),
        source="scanner",
        dish_slug="chicken_rice_bowl",
        ingredients=("broccoli", "chicken", "rice"),
        container="white_bowl",
        background="wooden_table",
        identity_key="k",
        scene_signature=tuple(signature),
        created_at=datetime.now(timezone.utc),
    )
    score = score_visual_match(
        parsed=parsed,
        candidate=candidate,
        scene_signature=signature,
    )
    assert score >= 0.95
