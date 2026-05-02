import pytest
from unittest.mock import MagicMock, patch

from src.infra.repositories.food_reference_repository import FoodReferenceRepository


def test_find_batch_by_normalized_names_returns_dict():
    """Verify batch lookup returns dict keyed by normalized name."""
    repo = FoodReferenceRepository()

    with patch.object(repo, "_to_dict") as mock_to_dict:
        mock_to_dict.side_effect = lambda m: {
            "name_normalized": m.name_normalized,
            "protein_100g": m.protein_100g,
        }

        with patch(
            "src.infra.repositories.food_reference_repository.SessionLocal"
        ) as mock_session:
            mock_model_1 = MagicMock()
            mock_model_1.name_normalized = "chicken breast"
            mock_model_1.protein_100g = 31.0

            mock_model_2 = MagicMock()
            mock_model_2.name_normalized = "rice"
            mock_model_2.protein_100g = 2.7

            mock_session.return_value.execute.return_value.scalars.return_value.all.return_value = [
                mock_model_1,
                mock_model_2,
            ]

            result = repo.find_batch_by_normalized_names(
                ["chicken breast", "rice", "unknown"]
            )

            assert "chicken breast" in result
            assert "rice" in result
            assert "unknown" not in result
            assert result["chicken breast"]["protein_100g"] == 31.0


def test_find_batch_by_normalized_names_empty_input():
    """Verify empty input returns empty dict."""
    repo = FoodReferenceRepository()
    result = repo.find_batch_by_normalized_names([])
    assert result == {}
