"""Heartbeat : un composant signale périodiquement qu'il est vivant."""
import time
from typing import Callable, Optional

from monitoring.metrics_store import MetricsStore


class Heartbeat:
    def __init__(
        self,
        metrics: MetricsStore,
        name: str = "service",
        clock: Callable[[], float] = time.time,
    ):
        self.metrics = metrics
        self.name = name
        self.clock = clock

    def beat(self) -> None:
        self.metrics.set_heartbeat(self.name, self.clock())

    def age(self) -> Optional[float]:
        return self.metrics.heartbeat_age(self.name, self.clock())

    def is_alive(self, max_age: float) -> bool:
        age = self.age()
        return age is not None and age <= max_age
