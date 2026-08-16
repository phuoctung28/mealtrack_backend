from __future__ import annotations

import pytest

from src.domain.services.nutrition_integrity_policy import (
    NUTRITION_INTEGRITY_POLICY_VERSION,
)
from src.domain.services.nutrition_integrity_state import (
    IntegrityState,
    IntegrityStateConflict,
    NutritionIntegrityStateMachine,
    build_integrity_input_digest,
    deterministic_integrity_lock_ids,
    is_publicly_eligible,
)


def _valid_payload() -> dict:
    return {
        "protein_100g": 10,
        "carbs_100g": 20,
        "fat_100g": 5,
        "fiber_100g": 2,
        "sugar_100g": 3,
        "serving_sizes": [{"name": "g", "grams": 1}],
    }


def test_digest_covers_parent_identity_legacy_json_and_ordered_children():
    first = build_integrity_input_digest(
        parent={"id": 7, "name": "Rice", "density": 1.0},
        legacy_serving_sizes=[{"name": "cup", "grams": 150}],
        serving_rows=[
            {"id": 2, "position": 1, "name": "cup", "grams": 150},
            {"id": 1, "position": 0, "name": "g", "grams": 1},
        ],
    )
    reordered = build_integrity_input_digest(
        parent={"density": 1.0, "name": "Rice", "id": 7},
        legacy_serving_sizes=[{"grams": 150, "name": "cup"}],
        serving_rows=[
            {"name": "g", "grams": 1, "position": 0, "id": 1},
            {"name": "cup", "grams": 150, "position": 1, "id": 2},
        ],
    )

    assert first == reordered
    assert len(first) == 64


def test_eligibility_fails_closed_for_missing_or_unsupported_materialized_state():
    assert not is_publicly_eligible(
        is_verified=True,
        integrity_status="unknown",
        integrity_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
    )


def test_parent_child_transactions_share_deterministic_lock_order():
    assert deterministic_integrity_lock_ids([9, 2, 9, 4]) == (2, 4, 9)
    assert not is_publicly_eligible(
        is_verified=True,
        integrity_status="valid",
        integrity_policy_version="nutrition_integrity_v0",
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
    )
    assert not is_publicly_eligible(
        is_verified=True,
        integrity_status="valid",
        integrity_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        active_policy_version="nutrition_integrity_v2",
    )


def test_state_machine_classifies_and_restores_with_a_forward_transition():
    machine = NutritionIntegrityStateMachine()
    digest = build_integrity_input_digest(
        parent=_valid_payload(), legacy_serving_sizes=None, serving_rows=[]
    )
    valid = machine.classify(
        _valid_payload(),
        is_verified=True,
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        input_digest=digest,
    )
    assert valid == IntegrityState(
        status="valid",
        policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        reason_code="accepted",
        input_digest=digest,
        review_reference=None,
    )

    quarantined = machine.quarantine(
        valid,
        expected_input_digest=digest,
        reason_code="manual_review",
        review_reference="review-7",
    )
    restored = machine.restore(
        quarantined,
        _valid_payload(),
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        input_digest=digest,
        expected_input_digest=digest,
        review_reference="review-8",
    )

    assert quarantined.status == "quarantined"
    assert restored.status == "valid"
    assert restored.review_reference == "review-8"


def test_state_machine_rejects_stale_compare_and_swap_digest():
    machine = NutritionIntegrityStateMachine()
    state = IntegrityState(
        status="valid",
        policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        reason_code="accepted",
        input_digest="a" * 64,
        review_reference=None,
    )

    with pytest.raises(IntegrityStateConflict):
        machine.quarantine(
            state,
            expected_input_digest="b" * 64,
            reason_code="manual_review",
            review_reference="review-7",
        )
