import unittest

from integrations.telegram.commands import CommandRouter
from app.supervisor import Supervisor
from runtime.service_state import Store


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class TestTelegramCommands(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock()
        self.store = Store(":memory:")
        self.sup = Supervisor(self.store, clock=self.clk)
        self.sup.recover()
        self.router = CommandRouter(self.sup)

    def tearDown(self):
        self.store.close()

    def d(self, cmd, *args):
        return self.router.dispatch(cmd, list(args), user_id=1)

    def test_ping(self):
        self.assertIn("ligne", self.d("ping"))

    def test_unknown_command(self):
        self.assertIn("inconnue", self.d("nope").lower())

    def test_help_lists_commands(self):
        out = self.d("help")
        self.assertIn("/status", out)
        self.assertIn("/scan", out)
        self.assertIn("Suivi", out)
        self.assertIn("Revente", out)

    def test_alias_scan_enqueues(self):
        out = self.d("scan")
        self.assertIn("tâche #", out)
        self.assertEqual(self.sup.queue_counts().get("pending"), 1)

    def test_alias_config_and_logs(self):
        self.assertIn("Configuration", self.d("config"))
        self.assertIn("JOURNAUX", self.d("logs"))

    def test_menu_alias(self):
        self.assertEqual(self.d("menu"), self.d("help"))

    def test_status_running(self):
        out = self.d("status")
        self.assertIn("ÉTAT", out)
        self.assertIn("actif", out)

    def test_health_has_status(self):
        out = self.d("health")
        self.assertTrue(out.startswith("SANTÉ"))

    def test_pause_resume(self):
        self.d("pause")
        self.assertTrue(self.sup.service_state.is_paused())
        self.assertIn("en pause", self.d("status"))
        self.d("resume")
        self.assertFalse(self.sup.service_state.is_paused())

    def test_safe_mode_requires_confirm(self):
        out = self.d("safe_mode_on")
        self.assertIn("Confirmez", out)
        self.assertFalse(self.sup.service_state.is_safe_mode())
        out2 = self.d("safe_mode_on", "confirm")
        self.assertTrue(self.sup.service_state.is_safe_mode())
        self.assertIn("MODE SÉCURITÉ", out2)

    def test_restart_failed_requires_confirm(self):
        out = self.d("restart_failed_jobs")
        self.assertIn("Confirmez", out)

    def test_ack_incident_usage(self):
        self.assertIn("Utilisation", self.d("ack_incident"))

    def test_scan_now_then_lastscan_and_tops(self):
        out = self.d("run_scan_now")
        self.assertIn("tâche #", out)
        # exécute le scan de façon synchrone via un worker
        processed = self.sup.workers[0].run_once(now=self.clk())
        self.assertTrue(processed)
        counts = self.sup.queue_counts()
        self.assertEqual(counts.get("success", 0), 1)

        last = self.d("lastscan")
        self.assertIn("DERNIER SCAN", last)
        tops = self.d("tops")
        self.assertIn("score :", tops)

    def test_metrics_after_scan(self):
        self.d("run_scan_now")
        self.sup.workers[0].run_once(now=self.clk())
        out = self.d("metrics")
        self.assertIn("analyses", out)
        self.assertIn("tâches réussies", out)

    def test_queue_command(self):
        out = self.d("queue")
        self.assertIn("FILE D'ATTENTE", out)

    def test_results_command(self):
        out = self.d("results")
        self.assertIn("RÉSULTATS", out)

    def test_member_management_flow(self):
        # une demande arrive, l'admin la voit, l'accepte, puis la révoque
        self.sup.members.request(555, "Alice")
        self.assertIn("555", self.d("requests"))
        self.d("accept", "555")
        self.assertTrue(self.sup.members.is_approved(555))
        self.assertIn("555", self.d("members"))
        self.d("revoke", "555")
        self.assertFalse(self.sup.members.is_approved(555))

    def test_accept_without_id_shows_usage(self):
        self.assertIn("Utilisation", self.d("accept"))


if __name__ == "__main__":
    unittest.main()
