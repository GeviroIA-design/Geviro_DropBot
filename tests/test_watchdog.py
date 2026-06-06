import unittest

from monitoring.metrics_store import MetricsStore
from runtime.job_queue import JobQueue
from runtime.service_state import Store
from runtime.watchdog import Watchdog


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class TestWatchdog(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock()
        self.store = Store(":memory:")
        self.queue = JobQueue(self.store, clock=self.clk)
        self.metrics = MetricsStore(self.store, clock=self.clk)
        self.wd = Watchdog(
            self.queue, self.metrics,
            job_timeout=10.0, heartbeat_max_age=10.0, clock=self.clk,
        )

    def tearDown(self):
        self.store.close()

    def test_no_anomaly_when_fresh(self):
        self.queue.enqueue("scan", "scan")  # reste pending, pas running
        self.metrics.set_heartbeat("worker-0", 0.0)
        self.assertEqual(self.wd.check(now=0.0), [])

    def test_detects_stuck_job(self):
        self.queue.enqueue("scan", "scan")
        job = self.queue.claim_next(now=0.0)  # started_at=0 -> running
        self.assertIsNotNone(job)
        self.metrics.set_heartbeat("worker-0", 0.0)
        anomalies = self.wd.check(now=20.0)
        types = {a["type"] for a in anomalies}
        self.assertIn("stuck_job", types)

    def test_detects_stale_heartbeat(self):
        self.metrics.set_heartbeat("worker-0", 0.0)
        anomalies = self.wd.check(now=20.0)
        types = {a["type"] for a in anomalies}
        self.assertIn("stale_heartbeat", types)

    def test_fresh_heartbeat_not_flagged(self):
        self.metrics.set_heartbeat("worker-0", 15.0)
        anomalies = self.wd.check(now=20.0)
        self.assertNotIn(
            "stale_heartbeat", {a["type"] for a in anomalies}
        )


if __name__ == "__main__":
    unittest.main()
