"""Unit tests for notification message templates (trial_expiry)."""

import pytest

from src.domain.services.notification_messages import get_messages


@pytest.mark.parametrize(
    "lang,gender",
    [
        ("en", "male"),
        ("en", "female"),
        ("vi", "male"),
        ("vi", "female"),
    ],
)
def test_trial_expiry_keys_exist(lang, gender):
    msgs = get_messages(lang, gender)
    assert "trial_expiry" in msgs
    assert "2d" in msgs["trial_expiry"]
    assert "1d" in msgs["trial_expiry"]
    assert msgs["trial_expiry"]["2d"]["body"]
    assert msgs["trial_expiry"]["1d"]["body"]
    # iOS Time Sensitive requires a non-empty alert title — banner is suppressed otherwise.
    assert msgs["trial_expiry"]["2d"]["title"] == "Nutree"
    assert msgs["trial_expiry"]["1d"]["title"] == "Nutree"


def test_trial_expiry_fallback_locale_returns_english():
    msgs = get_messages("fr", "male")
    assert "trial_expiry" in msgs
    assert "2 days" in msgs["trial_expiry"]["2d"]["body"]


def test_trial_expiry_vi_contains_vietnamese_phrasing():
    msgs = get_messages("vi", "male")
    assert "trial" in msgs["trial_expiry"]["2d"]["body"].lower()
    # Distinct buddy term for male VN.
    assert "bro" in msgs["trial_expiry"]["2d"]["body"]


def test_trial_expiry_en_female_uses_mate():
    msgs = get_messages("en", "female")
    assert "mate" in msgs["trial_expiry"]["2d"]["body"]


@pytest.mark.parametrize(
    "lang,gender",
    [
        ("en", "male"),
        ("en", "female"),
        ("vi", "male"),
        ("vi", "female"),
    ],
)
def test_hydration_reminder_keys_exist(lang, gender):
    msgs = get_messages(lang, gender)
    assert "hydration_reminder" in msgs
    assert "afternoon" in msgs["hydration_reminder"]
    assert "evening" in msgs["hydration_reminder"]
    assert msgs["hydration_reminder"]["afternoon"]["body_template"]
    assert msgs["hydration_reminder"]["evening"]["body_template"]


def test_hydration_type_enum_values_exist():
    from src.domain.model.notification.enums import NotificationType
    assert NotificationType.HYDRATION_REMINDER_AFTERNOON.value == "hydration_reminder_afternoon"
    assert NotificationType.HYDRATION_REMINDER_EVENING.value == "hydration_reminder_evening"
