import unittest

from runtime.scheduler import Scheduler


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class FakeQueue:
    def __init__(self):
        self.items = []

    def enqueue(self, name, job_type, max_attempts=1, payload=None,
                scheduled_at=None):
        self.items.append((name, job_type))
        return len(self.items)


class TestScheduler(unittest.TestCase):
    def test_due_after_interval(self):
        clk = FakeClock()
        s = Scheduler(clock=clk)
        s.add("scan", interval=10, job_type="scan", first_delay=0)
        self.assertEqual([j.name for j in s.due()], ["scan"])

        s.mark_ran("scan")
        self.assertEqual(s.due(), [])
        clk.advance(5)
        self.assertEqual(s.due(), [])
        clk.advance(5)
        self.assertEqual([j.name for j in s.due()], ["scan"])

    def test_tick_enqueues_and_reschedules(self):
        clk = FakeClock()
        s = Scheduler(clock=clk)
        q = FakeQueue()
        s.add("scan", interval=10, job_type="scan", first_delay=0)
        s.add("export", interval=100, job_type="export", first_delay=0)

        enqueued = s.tick(q)
        self.assertCountEqual(enqueued, ["scan", "export"])
        self.assertEqual(len(q.items), 2)

        clk.advance(10)
        enqueued2 = s.tick(q)
        self.assertEqual(enqueued2, ["scan"])  # seul scan est redû

    def test_disabled_job_not_due(self):
        clk = FakeClock()
        s = Scheduler(clock=clk)
        s.add("scan", interval=10, job_type="scan", first_delay=0)
        s.set_enabled("scan", False)
        self.assertEqual(s.due(), [])

    def test_first_delay_respected(self):
        clk = FakeClock()
        s = Scheduler(clock=clk)
        s.add("scan", interval=10, job_type="scan", first_delay=5)
        self.assertEqual(s.due(), [])
        clk.advance(5)
        self.assertEqual([j.name for j in s.due()], ["scan"])


if __name__ == "__main__":
    unittest.main()
