import unittest

from models.enums import CircuitState
from runtime.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class TestCircuitBreaker(unittest.TestCase):
    def test_opens_after_threshold(self):
        clk = FakeClock()
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60, clock=clk)
        self.assertTrue(cb.allow())
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow())

    def test_half_open_after_recovery_timeout(self):
        clk = FakeClock()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30, clock=clk)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow())
        clk.advance(31)
        self.assertTrue(cb.allow())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

    def test_success_closes_from_half_open(self):
        clk = FakeClock()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10, clock=clk)
        cb.record_failure()
        clk.advance(11)
        cb.allow()  # -> HALF_OPEN
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failures, 0)
        self.assertTrue(cb.allow())

    def test_failure_in_half_open_reopens(self):
        clk = FakeClock()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10, clock=clk)
        cb.record_failure()
        clk.advance(11)
        cb.allow()  # -> HALF_OPEN
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow())


if __name__ == "__main__":
    unittest.main()
