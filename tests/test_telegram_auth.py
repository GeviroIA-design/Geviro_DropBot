import unittest

from integrations.telegram.auth import Auth
from integrations.telegram.handlers import (
    MEMBER_FORBIDDEN,
    PENDING_MSG,
    RATE_LIMITED,
    REQUEST_SENT,
    UpdateHandler,
)
from monitoring.audit_log import AuditLog
from runtime.member_store import MemberStore
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


class TestHandlerRoles(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.audit = AuditLog(self.store)
        self.members = MemberStore(self.store)
        self.client = FakeClient()
        self.clk = FakeClock()

    def tearDown(self):
        self.store.close()

    def _handler(self, rate_limit=20):
        auth = Auth([1], rate_limit=rate_limit, window=60, clock=self.clk)
        return UpdateHandler(
            auth, DummyRouter(), self.audit, self.client, self.members
        )

    # --- admin ---
    def test_admin_dispatched_and_audited(self):
        h = self._handler()
        reply = h.handle_message(user_id=1, chat_id=1, text="/pause")
        self.assertEqual(reply, "dispatched:pause")  # admin = tout autorisé
        rows = self.audit.list()
        self.assertEqual(rows[0]["allowed"], 1)

    def test_rate_limited_admin(self):
        h = self._handler(rate_limit=1)
        first = h.handle_message(user_id=1, chat_id=1, text="/ping")
        second = h.handle_message(user_id=1, chat_id=1, text="/ping")
        self.assertEqual(first, "dispatched:ping")
        self.assertEqual(second, RATE_LIMITED)

    def test_non_command_ignored(self):
        h = self._handler()
        self.assertIsNone(h.handle_message(1, 1, "bonjour"))

    # --- inconnu -> demande d'accès ---
    def test_unknown_user_creates_request_and_notifies_admin(self):
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/status",
                                 name="Bob")
        self.assertEqual(reply, REQUEST_SENT)
        self.assertEqual(self.members.status(999), "pending")
        # l'admin (id 1) a été notifié de la demande
        self.assertTrue(
            any(cid == 1 and "demande" in txt.lower()
                for cid, txt in self.client.sent)
        )

    def test_pending_user_gets_waiting_message(self):
        self.members.request(999, "Bob")
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/status")
        self.assertEqual(reply, PENDING_MSG)

    # --- membre approuvé ---
    def test_member_allowed_read_command(self):
        self.members.approve(999, by=1)
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/status")
        self.assertEqual(reply, "dispatched:status")

    def test_member_blocked_on_admin_command(self):
        self.members.approve(999, by=1)
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/pause")
        self.assertEqual(reply, MEMBER_FORBIDDEN)

    def test_revoked_member_loses_access(self):
        self.members.approve(999, by=1)
        self.members.revoke(999, by=1)
        h = self._handler()
        reply = h.handle_message(user_id=999, chat_id=999, text="/status")
        self.assertNotEqual(reply, "dispatched:status")


if __name__ == "__main__":
    unittest.main()
