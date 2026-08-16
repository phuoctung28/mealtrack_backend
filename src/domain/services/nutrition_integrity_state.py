"""Versioned materialized state for canonical nutrition eligibility."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.domain.services.nutrition_integrity_policy import (
    ACCEPTED_REASON,
    NUTRITION_INTEGRITY_POLICY_VERSION,
    NutritionIntegrityPolicy,
)

SUPPORTED_NUTRITION_INTEGRITY_POLICY_VERSIONS = frozenset(
    {NUTRITION_INTEGRITY_POLICY_VERSION}
)
INTEGRITY_STATUSES = frozenset({"unknown", "valid", "quarantined"})


class IntegrityStateError(ValueError):
    """Raised when a materialized integrity transition is not safe."""


class IntegrityStateConflict(IntegrityStateError):
    """Raised when compare-and-swap input no longer matches the row."""


class UnsupportedIntegrityPolicy(IntegrityStateError):
    """Raised when a database policy is not implemented by this runtime."""


@dataclass(frozen=True)
class IntegrityState:
    status: str
    policy_version: str | None
    reason_code: str | None
    input_digest: str | None
    review_reference: str | None

    def __post_init__(self) -> None:
        if self.status not in INTEGRITY_STATUSES:
            raise IntegrityStateError(f"unsupported integrity status: {self.status}")


def ensure_supported_policy_version(version: str) -> str:
    """Fail closed instead of treating an unknown policy as V1-compatible."""
    if version not in SUPPORTED_NUTRITION_INTEGRITY_POLICY_VERSIONS:
        raise UnsupportedIntegrityPolicy(version)
    return version


def is_publicly_eligible(
    *,
    is_verified: bool,
    integrity_status: str | None,
    integrity_policy_version: str | None,
    active_policy_version: str | None,
) -> bool:
    """Return the only predicate allowed to publish a reference."""
    if not active_policy_version or not integrity_policy_version:
        return False
    if active_policy_version not in SUPPORTED_NUTRITION_INTEGRITY_POLICY_VERSIONS:
        return False
    return bool(
        is_verified
        and integrity_status == "valid"
        and integrity_policy_version == active_policy_version
    )


def build_integrity_input_digest(
    *,
    parent: Mapping[str, Any],
    legacy_serving_sizes: Any,
    serving_rows: list[Mapping[str, Any]],
) -> str:
    """Hash all nutrition/identity inputs that can affect eligibility."""
    ordered_rows = sorted(
        (dict(row) for row in serving_rows),
        key=lambda row: (
            _sort_value(row.get("position")),
            _sort_value(row.get("id")),
            str(row.get("name") or ""),
        ),
    )
    manifest = {
        "parent": _canonicalize(dict(parent)),
        "legacy_serving_sizes": _canonicalize(legacy_serving_sizes),
        "serving_rows": _canonicalize(ordered_rows),
    }
    encoded = json.dumps(
        manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def deterministic_integrity_lock_ids(
    ids: list[int] | tuple[int, ...],
) -> tuple[int, ...]:
    """Use one ordering for all parent/child multi-reference transactions."""
    return tuple(sorted({int(value) for value in ids}))


class NutritionIntegrityStateMachine:
    """Pure classifier and CAS transition rules shared by DB writers/CLIs."""

    def __init__(self, policy: NutritionIntegrityPolicy | None = None):
        self._policy = policy or NutritionIntegrityPolicy()

    def classify(
        self,
        payload: Mapping[str, Any],
        *,
        is_verified: bool,
        active_policy_version: str,
        input_digest: str,
        review_reference: str | None = None,
    ) -> IntegrityState:
        ensure_supported_policy_version(active_policy_version)
        if not is_verified:
            return IntegrityState("unknown", None, "unverified_reference", None, None)
        result = self._policy.evaluate(
            payload,
            require_energy=False,
            require_metric_basis=False,
        )
        return IntegrityState(
            status="valid" if result.accepted else "quarantined",
            policy_version=active_policy_version,
            reason_code=result.reason_code,
            input_digest=input_digest,
            review_reference=review_reference,
        )

    def quarantine(
        self,
        current: IntegrityState,
        *,
        expected_input_digest: str,
        reason_code: str,
        review_reference: str,
    ) -> IntegrityState:
        _require_digest(current, expected_input_digest)
        if not review_reference.strip():
            raise IntegrityStateError("quarantine requires a review reference")
        return IntegrityState(
            status="quarantined",
            policy_version=current.policy_version,
            reason_code=reason_code,
            input_digest=current.input_digest,
            review_reference=review_reference,
        )

    def restore(
        self,
        current: IntegrityState,
        payload: Mapping[str, Any],
        *,
        active_policy_version: str,
        input_digest: str,
        expected_input_digest: str,
        review_reference: str,
    ) -> IntegrityState:
        _require_digest(current, expected_input_digest)
        if not review_reference.strip():
            raise IntegrityStateError("restore requires a review reference")
        restored = self.classify(
            payload,
            is_verified=True,
            active_policy_version=active_policy_version,
            input_digest=input_digest,
            review_reference=review_reference,
        )
        if restored.status != "valid":
            raise IntegrityStateError(
                f"restore failed active policy: {restored.reason_code}"
            )
        return restored


def _require_digest(current: IntegrityState, expected: str) -> None:
    if not expected or current.input_digest != expected:
        raise IntegrityStateConflict("integrity input changed during transition")


def _sort_value(value: Any) -> tuple[int, str]:
    return (0, str(value)) if value is not None else (1, "")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IntegrityStateError("integrity manifest requires finite numbers")
        return format(value, ".15g")
    return value


__all__ = [
    "ACCEPTED_REASON",
    "INTEGRITY_STATUSES",
    "IntegrityState",
    "IntegrityStateConflict",
    "IntegrityStateError",
    "NutritionIntegrityStateMachine",
    "SUPPORTED_NUTRITION_INTEGRITY_POLICY_VERSIONS",
    "UnsupportedIntegrityPolicy",
    "build_integrity_input_digest",
    "deterministic_integrity_lock_ids",
    "ensure_supported_policy_version",
    "is_publicly_eligible",
]
