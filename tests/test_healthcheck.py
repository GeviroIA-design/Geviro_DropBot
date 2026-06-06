import unittest

from models.enums import CircuitState, HealthStatus
from monitoring.healthcheck import compute_health


def _health(**over):
    base = dict(
        heartbeat_age=5.0,
        heartbeat_max_age=90.0,
        breaker_states={},
        dead_letter_count=0,
        open_incidents=0,
        paused=False,
        safe_mode=False,
        last_scan_age=10.0,
        scan_interval=1800.0,
    )
    base.update(over)
    return compute_health(**base)


class TestHealthcheck(unittest.TestCase):
    def test_ok_when_all_green(self):
        self.assertEqual(_health()["status"], HealthStatus.OK.value)

    def test_down_when_heartbeat_missing(self):
        self.assertEqual(
            _health(heartbeat_age=None)["status"], HealthStatus.DOWN.value
        )

    def test_down_when_heartbeat_stale(self):
        self.assertEqual(
            _health(heartbeat_age=200.0)["status"], HealthStatus.DOWN.value
        )

    def test_degraded_when_breaker_open(self):
        h = _health(breaker_states={"scan": CircuitState.OPEN.value})
        self.assertEqual(h["status"], HealthStatus.DEGRADED.value)

    def test_degraded_when_dead_letters(self):
        self.assertEqual(
            _health(dead_letter_count=3)["status"], HealthStatus.DEGRADED.value
        )

    def test_degraded_when_safe_mode(self):
        self.assertEqual(
            _health(safe_mode=True)["status"], HealthStatus.DEGRADED.value
        )

    def test_degraded_when_scan_too_old(self):
        h = _health(last_scan_age=10000.0, scan_interval=1800.0)
        self.assertEqual(h["status"], HealthStatus.DEGRADED.value)

    def test_down_beats_degraded(self):
        h = _health(heartbeat_age=None, safe_mode=True, dead_letter_count=5)
        self.assertEqual(h["status"], HealthStatus.DOWN.value)


if __name__ == "__main__":
    unittest.main()
