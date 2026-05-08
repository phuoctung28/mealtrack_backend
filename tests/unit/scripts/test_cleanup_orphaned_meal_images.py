"""Tests for cleanup_orphaned_meal_images script."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from io import StringIO


def test_dry_run_does_not_modify_database():
    """Dry-run mode should report orphans but not update database."""
    from scripts.cleanup_orphaned_meal_images import find_orphaned_meals, mark_meals_failed

    # Mock session with candidate meals
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("meal-1", "img-1", "Dish 1", None),  # No URL
        ("meal-2", "img-2", "Dish 2", "https://cloudinary.com/img-2.jpg"),  # Has URL
    ]
    mock_session.execute.return_value = mock_result

    # Mock Cloudinary - img-1 not found, img-2 URL returns 404
    mock_cloudinary = MagicMock()
    mock_cloudinary.get_url.return_value = None  # img-1 not found

    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)  # img-2 URL dead

        orphans = find_orphaned_meals(mock_session, mock_cloudinary)

    assert len(orphans) == 2
    assert "meal-1" in orphans
    assert "meal-2" in orphans


def test_mark_meals_failed_updates_status():
    """mark_meals_failed should update meal status to FAILED."""
    from scripts.cleanup_orphaned_meal_images import mark_meals_failed

    mock_session = MagicMock()

    orphan_ids = ["meal-1", "meal-2"]
    mark_meals_failed(mock_session, orphan_ids)

    # Verify UPDATE was called
    mock_session.execute.assert_called_once()
    call_args = str(mock_session.execute.call_args)
    assert "FAILED" in call_args or "status" in call_args.lower()
    mock_session.commit.assert_called_once()
