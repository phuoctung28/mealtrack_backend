"""Tests for EmailTemplateRenderer."""

import pytest

from src.infra.services.email_template_renderer import EmailTemplateRenderer


@pytest.fixture
def renderer():
    return EmailTemplateRenderer()


def test_render_welcome_template(renderer):
    html = renderer.render(
        "welcome",
        {
            "subject": "Welcome!",
            "first_name": "Alex",
            "tdee": 2000,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "2000 kcal" in html
    assert "Log Your First Meal" in html
    assert "Unsubscribe" in html


def test_render_reengagement_template(renderer):
    html = renderer.render(
        "reengagement",
        {
            "subject": "We miss you",
            "first_name": "Alex",
            "streak_days": 5,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "5 day streak" in html
    assert "Pick Up Where You Left Off" in html


def test_render_with_missing_optional_field(renderer):
    html = renderer.render(
        "reengagement",
        {
            "subject": "We miss you",
            "first_name": "Alex",
            "streak_days": 0,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "day streak" not in html  # Hidden when streak is 0


def test_render_raises_for_unknown_template(renderer):
    with pytest.raises(ValueError, match="not found"):
        renderer.render("nonexistent", {})
