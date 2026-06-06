"""Circuit breaker par type de job (horloge injectable pour les tests)."""
import time
from typing import Callable, Dict, Optional

from models.enums import CircuitState


class CircuitBreaker:
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        clock: Callable[[], float] = time.time,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at: Optional[float] = None

    def allow(self) -> bool:
        """Le breaker autorise-t-il une nouvelle tentative maintenant ?"""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.opened_at is None:
                return True
            if self.clock() - self.opened_at >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN : on laisse passer une tentative de sonde.
        return True

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.failures >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = self.clock()

    def snapshot(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "opened_at": self.opened_at,
        }
