"""Watchdog : détecte jobs bloqués et heartbeats périmés."""
import time
from typing import Any, Callable, Dict, List, Optional

from monitoring.metrics_store import MetricsStore
from runtime.job_queue import JobQueue


class Watchdog:
    def __init__(
        self,
        queue: JobQueue,
        metrics: MetricsStore,
        job_timeout: float,
        heartbeat_max_age: float,
        clock: Callable[[], float] = time.time,
    ):
        self.queue = queue
        self.metrics = metrics
        self.job_timeout = job_timeout
        self.heartbeat_max_age = heartbeat_max_age
        self.clock = clock

    def check(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retourne la liste des anomalies détectées (sans agir)."""
        now = now if now is not None else self.clock()
        anomalies: List[Dict[str, Any]] = []

        for job in self.queue.find_stuck(self.job_timeout, now):
            anomalies.append(
                {
                    "type": "stuck_job",
                    "job_id": job["id"],
                    "name": job["name"],
                    "detail": (
                        f"job {job['id']} ({job['name']}) running > "
                        f"{self.job_timeout:.0f}s"
                    ),
                }
            )

        for name, ts in self.metrics.all_heartbeats().items():
            age = now - ts
            if age > self.heartbeat_max_age:
                anomalies.append(
                    {
                        "type": "stale_heartbeat",
                        "component": name,
                        "detail": f"heartbeat '{name}' stale ({age:.0f}s)",
                    }
                )

        return anomalies
