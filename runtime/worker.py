"""Worker : réserve un job, l'exécute, applique retry + circuit breaker."""
import json
import time
from typing import Callable, Dict, Optional

from models.enums import IncidentSeverity
from runtime.circuit_breaker import CircuitBreaker
from runtime.job_queue import JobQueue
from runtime.retry_policy import RetryPolicy


class Worker:
    def __init__(
        self,
        name: str,
        queue: JobQueue,
        registry: Dict[str, Callable[[dict], object]],
        retry_policy: RetryPolicy,
        metrics,
        incidents,
        alerts,
        breaker_for: Callable[[str], CircuitBreaker],
        is_blocked: Callable[[], bool],
        clock: Callable[[], float] = time.time,
    ):
        self.name = name
        self.queue = queue
        self.registry = registry
        self.retry_policy = retry_policy
        self.metrics = metrics
        self.incidents = incidents
        self.alerts = alerts
        self.breaker_for = breaker_for
        self.is_blocked = is_blocked
        self.clock = clock

    @staticmethod
    def _payload(job: dict) -> dict:
        raw = job.get("payload")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw:
            try:
                return json.loads(raw)
            except ValueError:
                return {}
        return {}

    def run_once(self, now: Optional[float] = None) -> bool:
        """Traite au plus un job. Retourne True si un job a été pris."""
        if self.is_blocked():
            return False
        now = now if now is not None else self.clock()

        job = self.queue.claim_next(now)
        if job is None:
            return False

        job_type = job["type"]
        breaker = self.breaker_for(job_type)
        attempts = job["attempts"] + 1

        if not breaker.allow():
            self.queue.mark_retrying(
                job["id"],
                scheduled_at=now + breaker.recovery_timeout,
                error="coupe-circuit ouvert",
                attempts=job["attempts"],
            )
            self.metrics.incr("jobs_circuit_skipped")
            return True

        handler = self.registry.get(job_type)
        if handler is None:
            self.queue.mark_dead_letter(
                job["id"], f"aucun gestionnaire pour le type '{job_type}'",
                attempts,
            )
            self.incidents.record(
                IncidentSeverity.WARNING.value,
                "worker",
                f"aucun gestionnaire pour le type de tâche '{job_type}'",
            )
            return True

        try:
            handler(self._payload(job))
            self.queue.mark_success(job["id"])
            breaker.record_success()
            self.metrics.incr("jobs_success")
        except Exception as exc:  # noqa: BLE001 - on capture tout côté worker
            breaker.record_failure()
            self.metrics.incr("jobs_failed")
            err = f"{type(exc).__name__}: {exc}"
            if self.retry_policy.should_retry(attempts):
                delay = self.retry_policy.compute_delay(attempts)
                self.queue.mark_retrying(
                    job["id"],
                    scheduled_at=now + delay,
                    error=err,
                    attempts=attempts,
                )
                self.metrics.incr("jobs_retried")
            else:
                self.queue.mark_dead_letter(job["id"], err, attempts)
                self.metrics.incr("jobs_dead_letter")
                self.alerts.raise_alert(
                    IncidentSeverity.CRITICAL.value,
                    job_type,
                    f"tâche '{job['name']}' abandonnée après "
                    f"{attempts} essais : {err}",
                )
        return True
