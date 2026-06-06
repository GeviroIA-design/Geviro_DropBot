import unittest

from monitoring.incident_store import IncidentStore
from monitoring.metrics_store import MetricsStore
from runtime.job_queue import JobQueue
from runtime.recovery import recover_on_start
from runtime.service_state import ServiceState, Store


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock()
        self.store = Store(":memory:")
        self.queue = JobQueue(self.store, clock=self.clk)
        self.ss = ServiceState(self.store)
        self.inc = IncidentStore(self.store, clock=self.clk)
        self.metrics = MetricsStore(self.store, clock=self.clk)

    def tearDown(self):
        self.store.close()

    def test_requeues_running_jobs(self):
        self.queue.enqueue("scan", "scan")
        self.queue.claim_next(now=self.clk())  # -> running
        summary = recover_on_start(
            self.queue, self.ss, self.inc, self.metrics, self.clk
        )
        self.assertEqual(summary["requeued_running_jobs"], 1)
        self.assertEqual(self.queue.counts().get("pending"), 1)
        self.assertEqual(self.queue.counts().get("running", 0), 0)

    def test_clears_stale_heartbeats(self):
        self.metrics.set_heartbeat("worker-0", 0.0)  # vieux heartbeat
        self.assertNotEqual(self.metrics.all_heartbeats(), {})
        recover_on_start(self.queue, self.ss, self.inc, self.metrics, self.clk)
        self.assertEqual(self.metrics.all_heartbeats(), {})

    def test_marks_started_and_logs_incident(self):
        recover_on_start(self.queue, self.ss, self.inc, self.metrics, self.clk)
        self.assertIsNotNone(self.ss.started_at())
        incidents = self.inc.list()
        self.assertTrue(any(i["source"] == "recovery" for i in incidents))

    def test_works_without_metrics(self):
        # metrics est optionnel : ne doit pas planter si absent.
        summary = recover_on_start(self.queue, self.ss, self.inc)
        self.assertIn("requeued_running_jobs", summary)


if __name__ == "__main__":
    unittest.main()
