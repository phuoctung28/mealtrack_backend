"""Circuit breaker for AI provider health tracking."""
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ModelCircuit:
    """State for a single model's circuit."""

    state: CircuitState = CircuitState.CLOSED
    failure_timestamps: List[float] = field(default_factory=list)
    opened_at: Optional[float] = None

    def reset(self) -> None:
        """Reset to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_timestamps = []
        self.opened_at = None


class ProviderCircuitBreaker:
    """
    Circuit breaker tracking health per model.

    Thread-safe singleton that tracks failures across all requests.
    Opens circuit after failure_threshold failures within failure_window_seconds.
    """

    TRIPPING_ERRORS = {503, 429, 500, 502, 504}

    def __init__(
        self,
        failure_threshold: int = 5,
        failure_window_seconds: int = 60,
        cooldown_seconds: int = 30,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._failure_window = failure_window_seconds
        self._cooldown = cooldown_seconds
        self._circuits: Dict[str, ModelCircuit] = {}
        self._lock = threading.Lock()

    def get_state(self, model: str) -> CircuitState:
        """Get current circuit state for a model."""
        with self._lock:
            circuit = self._get_or_create_circuit(model)
            self._maybe_transition_state(circuit)
            return circuit.state

    def record_failure(self, model: str) -> None:
        """Record a failure for a model."""
        with self._lock:
            circuit = self._get_or_create_circuit(model)
            now = time.time()

            if circuit.state == CircuitState.HALF_OPEN:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = now
                logger.warning(f"[CIRCUIT-REOPEN] model={model}")
                return

            circuit.failure_timestamps.append(now)
            self._prune_old_failures(circuit, now)

            if len(circuit.failure_timestamps) >= self._failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = now
                logger.warning(
                    f"[CIRCUIT-OPEN] model={model} | "
                    f"failures={len(circuit.failure_timestamps)}"
                )

    def record_success(self, model: str) -> None:
        """Record a success for a model."""
        with self._lock:
            circuit = self._get_or_create_circuit(model)

            if circuit.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info(f"[CIRCUIT-CLOSE] model={model}")

            circuit.reset()

    def filter_available(self, models: List[str]) -> List[str]:
        """Return models with CLOSED or HALF_OPEN circuits."""
        return [m for m in models if self.get_state(m) != CircuitState.OPEN]

    def should_trip(self, error: Union[int, str]) -> bool:
        """Check if an error should trip the circuit."""
        if isinstance(error, int):
            return error in self.TRIPPING_ERRORS
        if isinstance(error, str):
            error_lower = error.lower()
            return "timeout" in error_lower or "unavailable" in error_lower
        return False

    def _get_or_create_circuit(self, model: str) -> ModelCircuit:
        """Get or create circuit for model. Caller must hold lock."""
        if model not in self._circuits:
            self._circuits[model] = ModelCircuit()
        return self._circuits[model]

    def _maybe_transition_state(self, circuit: ModelCircuit) -> None:
        """Check if circuit should transition. Caller must hold lock."""
        if circuit.state != CircuitState.OPEN:
            return

        if circuit.opened_at is None:
            return

        elapsed = time.time() - circuit.opened_at
        if elapsed >= self._cooldown:
            circuit.state = CircuitState.HALF_OPEN
            logger.debug(f"[CIRCUIT-HALF-OPEN] after {elapsed:.1f}s cooldown")

    def _prune_old_failures(self, circuit: ModelCircuit, now: float) -> None:
        """Remove failures outside the window. Caller must hold lock."""
        cutoff = now - self._failure_window
        circuit.failure_timestamps = [
            ts for ts in circuit.failure_timestamps if ts > cutoff
        ]
