"""Politique de retry avec backoff exponentiel (déterministe, testable)."""
from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 2.0
    factor: float = 2.0
    max_delay: float = 300.0

    def should_retry(self, attempts: int) -> bool:
        """attempts = nombre d'essais DÉJÀ effectués (échecs inclus)."""
        return attempts < self.max_attempts

    def compute_delay(self, attempts: int) -> float:
        """Délai avant le prochain essai après `attempts` échecs (>=1)."""
        if attempts < 1:
            attempts = 1
        delay = self.base_delay * (self.factor ** (attempts - 1))
        return float(min(self.max_delay, delay))
