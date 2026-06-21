"""Failing contract tests for the D1-D3 retention campaign message catalog.

`get_retention_messages` does not exist yet in
`src.domain.services.onboarding_retention_messages` — tests are intentionally
red until Phase 3 implements the catalog.
"""

import pytest

from src.domain.services.onboarding_retention_messages import (  # noqa: F401
    get_retention_messages,
)

# All seven campaign notification types defined in the campaign spec.
ALL_TYPES = [
    "d1_night_anchor",
    "d2_morning_steps_sync",
    "d2_lunch_refuel",
    "d2_hydration_slump",
    "d2_daily_summary",
    "d3_churn_preemption",
    "d3_premium_asset_lock",
]


# ---------------------------------------------------------------------------
# Coverage: all types × language × gender
# ---------------------------------------------------------------------------


def test_all_seven_types_have_en_male_copy():
    """Every campaign type returns non-empty title + body for en / male."""
    msgs = get_retention_messages("en", "male")
    for ntype in ALL_TYPES:
        assert ntype in msgs, f"Missing key: {ntype}"
        entry = msgs[ntype]
        assert entry.get("title"), f"{ntype}: title is empty (en/male)"
        assert entry.get("body"), f"{ntype}: body is empty (en/male)"


def test_all_seven_types_have_vi_female_copy():
    """Every campaign type returns non-empty title + body for vi / female."""
    msgs = get_retention_messages("vi", "female")
    for ntype in ALL_TYPES:
        assert ntype in msgs, f"Missing key: {ntype}"
        entry = msgs[ntype]
        assert entry.get("title"), f"{ntype}: title is empty (vi/female)"
        assert entry.get("body"), f"{ntype}: body is empty (vi/female)"


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


def test_missing_lang_falls_back_to_en():
    """Unknown language code returns English copy (not a KeyError)."""
    msgs_unknown = get_retention_messages("fr", "male")
    msgs_en = get_retention_messages("en", "male")

    for ntype in ALL_TYPES:
        assert ntype in msgs_unknown, f"Fallback missing key: {ntype}"
        assert msgs_unknown[ntype]["body"] == msgs_en[ntype]["body"], (
            f"{ntype}: fallback body does not match en/male"
        )


# ---------------------------------------------------------------------------
# Dynamic copy: d2_daily_summary percentage interpolation
# ---------------------------------------------------------------------------


def test_dynamic_copy_d2_summary_on_target():
    """d2_daily_summary body for on-target (percentage=95) mentions the value."""
    msgs = get_retention_messages("en", "male", context={"percentage": 95})
    body = msgs["d2_daily_summary"]["body"]
    assert "95" in body, f"Expected '95' in d2_daily_summary body, got: {body!r}"


def test_dynamic_copy_d2_summary_vi_on_target():
    """Vietnamese d2_daily_summary also interpolates percentage."""
    msgs = get_retention_messages("vi", "female", context={"percentage": 88})
    body = msgs["d2_daily_summary"]["body"]
    assert "88" in body, f"Expected '88' in vi d2_daily_summary body, got: {body!r}"


# ---------------------------------------------------------------------------
# Notification type length guard (DB constraint: max 30 chars)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ntype", ALL_TYPES)
def test_notification_type_within_30_chars(ntype):
    """Every campaign notification_type fits the DB varchar(30) column."""
    assert len(ntype) <= 30, (
        f"notification_type {ntype!r} is {len(ntype)} chars — exceeds 30-char limit"
    )
