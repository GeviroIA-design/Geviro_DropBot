import unittest

from integrations.telegram.auth import Auth
from integrations.telegram.handlers import RATE_LIMITED, REFUSAL, UpdateHandler
from monitoring.audit_log import AuditLog
from runtime.service_state import Store


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class FakeClient:
    enabled = True

    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return True


class DummyRouter:
    def dispatch(self, command, args, user_id):
        return f"dispatched:{command}"


class TestAuth(unittest.TestCase):
    def test_is_admin(self):
        a = Auth([1, 2])
        self.assertTrue(a.is_admin(1))
        self.assertTrue(a.is_admin("2"))
        self.assertFalse(a.is_admin(3))
        self.assertFalse(a.is_admin("abc"))

    def test_rate_limit_blocks_then_recovers(self):
        clk = FakeClock()
        a = Auth([1], rate_limit=3, window=60, clock=clk)
        self.assertTrue(a.allow_rate(1))
        self.assertTrue(a.allow_rate(1))
        self.assertTrue(a.allow_rate(1))
        self.assertFalse(a.allow_rate(1))  # 4e bloqué
        clk.advance(61)
        self.assertTrue(a.allow_rate(1))  # fenêtre repartie


class TestHandlerAuth(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.audit = AuditLog(self.store)
        self.client = FakeClient()
        self.clk = FakeClock()

    def tearDown(self):
        self.store.close()

    def _handler(self, rate_limit=20):
        auth = Auth([1], rate_limit=rate_limit, window=60, clock=self.clk)
        return UpdateHandler(auth, DummyRouter(), self.audit, self.client)

    def test_non_admin_refused(self):
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/status")
        self.assertEqual(reply, REFUSAL)
        self.assertEqual(self.client.sent[-1], (999, REFUSAL))
        rows = self.audit.list()
        self.assertEqual(rows[0]["allowed"], 0)
        self.assertEqual(rows[0]["result"], "denied")

    def test_admin_dispatched_and_audited(self):
        h = self._handler()
        reply = h.handle_message(user_id=1, chat_id=1, text="/ping")
        self.assertEqual(reply, "dispatched:ping")
        rows = self.audit.list()
        self.assertEqual(rows[0]["allowed"], 1)
        self.assertEqual(rows[0]["command"], "ping")

    def test_rate_limited_admin(self):
        h = self._handler(rate_limit=1)
        first = h.handle_message(user_id=1, chat_id=1, text="/ping")
        second = h.handle_message(user_id=1, chat_id=1, text="/ping")
        self.assertEqual(first, "dispatched:ping")
        self.assertEqual(second, RATE_LIMITED)

    def test_non_command_ignored(self):
        h = self._handler()
        reply = h.handle_message(user_id=1, chat_id=1, text="bonjour")
        self.assertIsNone(reply)


if __name__ == "__main__":
    unittest.main()
