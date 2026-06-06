"""File de jobs persistée (table `jobs` du Store partagé)."""
import json
import time
from typing import Any, Dict, List, Optional

from models.enums import JobState
from runtime.service_state import Store


class JobQueue:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def enqueue(
        self,
        name: str,
        job_type: str,
        payload: Optional[dict] = None,
        max_attempts: int = 1,
        scheduled_at: Optional[float] = None,
    ) -> int:
        now = self.clock()
        return self.store.execute(
            "INSERT INTO jobs(name, type, state, payload, attempts, "
            "max_attempts, created_at, updated_at, scheduled_at) "
            "VALUES(?, ?, ?, ?, 0, ?, ?, ?, ?)",
            (
                name,
                job_type,
                JobState.PENDING.value,
                json.dumps(payload or {}),
                max_attempts,
                now,
                now,
                scheduled_at if scheduled_at is not None else now,
            ),
        )

    def claim_next(self, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Réserve atomiquement le prochain job exécutable -> état running."""
        now = now if now is not None else self.clock()
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE state IN (?, ?) AND scheduled_at <= ? "
                "ORDER BY scheduled_at, id LIMIT 1",
                (JobState.PENDING.value, JobState.RETRYING.value, now),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE jobs SET state=?, started_at=?, finished_at=NULL, "
                "updated_at=? WHERE id=?",
                (JobState.RUNNING.value, now, now, row["id"]),
            )
            job = dict(row)
            job["state"] = JobState.RUNNING.value
            job["started_at"] = now
            return job

    def _finish(self, job_id: int, state: str, error: Optional[str]) -> None:
        now = self.clock()
        self.store.execute(
            "UPDATE jobs SET state=?, last_error=?, finished_at=?, "
            "updated_at=? WHERE id=?",
            (state, error, now, now, job_id),
        )

    def mark_success(self, job_id: int) -> None:
        self._finish(job_id, JobState.SUCCESS.value, None)

    def mark_dead_letter(self, job_id: int, error: str, attempts: int) -> None:
        now = self.clock()
        self.store.execute(
            "UPDATE jobs SET state=?, last_error=?, attempts=?, finished_at=?, "
            "updated_at=? WHERE id=?",
            (JobState.DEAD_LETTER.value, error, attempts, now, now, job_id),
        )

    def mark_failed(self, job_id: int, error: str) -> None:
        self._finish(job_id, JobState.FAILED.value, error)

    def mark_retrying(
        self, job_id: int, scheduled_at: float, error: str, attempts: int
    ) -> None:
        now = self.clock()
        self.store.execute(
            "UPDATE jobs SET state=?, scheduled_at=?, last_error=?, attempts=?, "
            "started_at=NULL, updated_at=? WHERE id=?",
            (JobState.RETRYING.value, scheduled_at, error, attempts, now, job_id),
        )

    def cancel(self, job_id: int) -> bool:
        now = self.clock()
        rid = self.store.execute(
            "UPDATE jobs SET state=?, updated_at=? WHERE id=? AND state IN (?, ?)",
            (
                JobState.CANCELLED.value,
                now,
                job_id,
                JobState.PENDING.value,
                JobState.RETRYING.value,
            ),
        )
        return rid is not None

    def get(self, job_id: int) -> Optional[Dict[str, Any]]:
        return self.store.query_one("SELECT * FROM jobs WHERE id=?", (job_id,))

    def list(
        self, states: Optional[List[str]] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        if states:
            placeholders = ",".join("?" for _ in states)
            return self.store.query(
                f"SELECT * FROM jobs WHERE state IN ({placeholders}) "
                f"ORDER BY id DESC LIMIT ?",
                (*states, limit),
            )
        return self.store.query(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
        )

    def counts(self) -> Dict[str, int]:
        rows = self.store.query(
            "SELECT state, COUNT(*) AS n FROM jobs GROUP BY state"
        )
        return {r["state"]: r["n"] for r in rows}

    def find_stuck(
        self, timeout: float, now: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        now = now if now is not None else self.clock()
        return self.store.query(
            "SELECT * FROM jobs WHERE state=? AND started_at IS NOT NULL "
            "AND started_at < ?",
            (JobState.RUNNING.value, now - timeout),
        )

    def requeue_running(self, now: Optional[float] = None) -> int:
        """Recovery au démarrage : tout job 'running' redevient 'pending'."""
        now = now if now is not None else self.clock()
        with self.store.connection() as conn:
            cur = conn.execute(
                "UPDATE jobs SET state=?, scheduled_at=?, started_at=NULL, "
                "updated_at=? WHERE state=?",
                (JobState.PENDING.value, now, now, JobState.RUNNING.value),
            )
            return cur.rowcount

    def requeue_job(self, job_id: int, now: Optional[float] = None) -> None:
        now = now if now is not None else self.clock()
        self.store.execute(
            "UPDATE jobs SET state=?, scheduled_at=?, started_at=NULL, "
            "updated_at=? WHERE id=?",
            (JobState.PENDING.value, now, now, job_id),
        )

    def restart_failed(self, now: Optional[float] = None) -> int:
        """Relance les jobs failed/dead_letter (attempts remis à 0)."""
        now = now if now is not None else self.clock()
        with self.store.connection() as conn:
            cur = conn.execute(
                "UPDATE jobs SET state=?, scheduled_at=?, attempts=0, "
                "last_error=NULL, started_at=NULL, updated_at=? "
                "WHERE state IN (?, ?)",
                (
                    JobState.PENDING.value,
                    now,
                    now,
                    JobState.FAILED.value,
                    JobState.DEAD_LETTER.value,
                ),
            )
            return cur.rowcount
