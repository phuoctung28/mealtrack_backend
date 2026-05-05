import pytest
from src.domain.services.meal_image_cache.name_canonicalizer import slug


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Grilled Lemon Salmon", "grilled-lemon-salmon"),
        ("  Cơm Chiên Tôm Mực  ", "com-chien-tom-muc"),
        ("PHỞ BÒ!", "pho-bo"),
        ("Mac & Cheese", "mac-cheese"),
        ("Chicken---Soup", "chicken-soup"),
    ],
)
def test_slug_normalizes_names(raw, expected):
    assert slug(raw) == expected


def test_slug_rejects_empty():
    with pytest.raises(ValueError):
        slug("   ")
