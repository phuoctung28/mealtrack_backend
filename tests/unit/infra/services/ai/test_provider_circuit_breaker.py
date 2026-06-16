import pytest
import time
from unittest.mock import patch
from src.infra.ai.circuit_breaker import (
    ProviderCircuitBreaker,
    CircuitState,
)


@pytest.fixture
def breaker():
    return ProviderCircuitBreaker(
        failure_threshold=3,
        failure_window_seconds=60,
        cooldown_seconds=10,
    )


class TestCircuitState:
    def test_initial_state_is_closed(self, breaker):
        assert breaker.get_state("model-a") == CircuitState.CLOSED

    def test_state_transitions_to_open_after_threshold(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")
        assert breaker.get_state("model-a") == CircuitState.OPEN

    def test_state_below_threshold_stays_closed(self, breaker):
        breaker.record_failure("model-a")
        breaker.record_failure("model-a")
        assert breaker.get_state("model-a") == CircuitState.CLOSED

    def test_success_resets_failure_count(self, breaker):
        breaker.record_failure("model-a")
        breaker.record_failure("model-a")
        breaker.record_success("model-a")
        breaker.record_failure("model-a")
        breaker.record_failure("model-a")
        assert breaker.get_state("model-a") == CircuitState.CLOSED


class TestCooldown:
    def test_open_circuit_transitions_to_half_open_after_cooldown(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")
        assert breaker.get_state("model-a") == CircuitState.OPEN

        with patch("time.time", return_value=time.time() + 11):
            assert breaker.get_state("model-a") == CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")

        with patch("time.time", return_value=time.time() + 11):
            assert breaker.get_state("model-a") == CircuitState.HALF_OPEN
            breaker.record_success("model-a")
            assert breaker.get_state("model-a") == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")

        with patch("time.time", return_value=time.time() + 11):
            assert breaker.get_state("model-a") == CircuitState.HALF_OPEN
            breaker.record_failure("model-a")
            assert breaker.get_state("model-a") == CircuitState.OPEN


class TestFailureWindow:
    def test_old_failures_expire(self, breaker):
        breaker.record_failure("model-a")
        breaker.record_failure("model-a")

        with patch("time.time", return_value=time.time() + 61):
            breaker.record_failure("model-a")
            assert breaker.get_state("model-a") == CircuitState.CLOSED


class TestMultipleModels:
    def test_circuits_are_independent(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")

        assert breaker.get_state("model-a") == CircuitState.OPEN
        assert breaker.get_state("model-b") == CircuitState.CLOSED

    def test_is_available_returns_correct_models(self, breaker):
        for _ in range(3):
            breaker.record_failure("model-a")

        models = ["model-a", "model-b", "model-c"]
        available = breaker.filter_available(models)
        assert available == ["model-b", "model-c"]


class TestErrorClassification:
    def test_503_trips_circuit(self, breaker):
        assert breaker.should_trip(503) is True

    def test_429_trips_circuit(self, breaker):
        assert breaker.should_trip(429) is True

    def test_500_trips_circuit(self, breaker):
        assert breaker.should_trip(500) is True

    def test_400_does_not_trip(self, breaker):
        assert breaker.should_trip(400) is False

    def test_timeout_string_trips(self, breaker):
        assert breaker.should_trip("timeout") is True
        assert breaker.should_trip("Timeout") is True
