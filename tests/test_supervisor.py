import unittest

from app.supervisor import Supervisor
from runtime.service_state import Store


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class TestSupervisorWatchdog(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock(1000.0)
        self.store = Store(":memory:")
        self.sup = Supervisor(self.store, clock=self.clk)
        self.sup.recover()

    def tearDown(self):
        self.store.close()

    def _watchdog_incidents(self):
        return [
            i for i in self.sup.incidents.list(500)
            if i["source"] == "watchdog"
        ]

    def test_freeze_does_not_raise_false_alert(self):
        """Veille machine / saut d'horloge : aucune fausse alerte."""
        self.sup.tick(now=1000.0)
        self.sup.metrics.set_heartbeat("worker-0", 1000.0)
        # Tick très longtemps après (ex: 9h de veille) -> gel détecté.
        anomalies = self.sup.tick(now=1000.0 + 34876.0)
        self.assertEqual(anomalies, [])
        self.assertEqual(self._watchdog_incidents(), [])

    def test_dead_worker_still_detected_in_steady_state(self):
        """Sans gel (ticks réguliers), un worker mort EST bien détecté."""
        self.sup.tick(now=2000.0)
        self.sup.metrics.set_heartbeat("worker-0", 2000.0)
        # Le superviseur continue de ticker normalement (pas de gel),
        # mais worker-0 ne bat plus. On avance par pas de 1s.
        t = 2000.0
        for _ in range(int(self.sup.settings.heartbeat_max_age) + 10):
            t += 1.0
            self.sup.tick(now=t)
        dead = [i for i in self._watchdog_incidents()
                if "worker-0" in i["message"]]
        self.assertTrue(len(dead) >= 1)

    def test_alert_message_is_stable(self):
        """Le message d'alerte ne contient pas le nombre de secondes
        (sinon l'anti-spam ne marche pas)."""
        msg = Supervisor._alert_message(
            {"type": "stale_heartbeat", "component": "worker-1",
             "detail": "heartbeat 'worker-1' stale (123s)"}
        )
        self.assertIn("worker-1", msg)
        self.assertNotIn("123", msg)


if __name__ == "__main__":
    unittest.main()
