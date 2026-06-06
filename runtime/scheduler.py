"""Scheduler de jobs récurrents. N'exécute pas : il met en file."""
import time
from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass
class ScheduledJob:
    name: str
    interval: float
    job_type: str
    max_attempts: int = 1
    enabled: bool = True
    next_run: float = 0.0


class Scheduler:
    def __init__(self, clock: Callable[[], float] = time.time):
        self.clock = clock
        self.jobs: Dict[str, ScheduledJob] = {}

    def add(
        self,
        name: str,
        interval: float,
        job_type: str,
        max_attempts: int = 1,
        enabled: bool = True,
        first_delay: float = 0.0,
    ) -> None:
        self.jobs[name] = ScheduledJob(
            name=name,
            interval=interval,
            job_type=job_type,
            max_attempts=max_attempts,
            enabled=enabled,
            next_run=self.clock() + first_delay,
        )

    def set_enabled(self, name: str, value: bool) -> None:
        if name in self.jobs:
            self.jobs[name].enabled = value

    def set_interval(self, name: str, interval: float) -> None:
        if name in self.jobs:
            self.jobs[name].interval = interval

    def due(self) -> List[ScheduledJob]:
        now = self.clock()
        return [
            j for j in self.jobs.values() if j.enabled and now >= j.next_run
        ]

    def mark_ran(self, name: str) -> None:
        job = self.jobs.get(name)
        if job:
            job.next_run = self.clock() + job.interval

    def tick(self, queue) -> List[str]:
        """Met en file tous les jobs dûs. Retourne les noms enfilés."""
        enqueued: List[str] = []
        for job in self.due():
            queue.enqueue(
                name=job.name,
                job_type=job.job_type,
                max_attempts=job.max_attempts,
            )
            self.mark_ran(job.name)
            enqueued.append(job.name)
        return enqueued
