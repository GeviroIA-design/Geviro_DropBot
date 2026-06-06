"""Traitement des updates Telegram : parsing, auth, audit, dispatch, réponse."""
from typing import Optional, Tuple

from integrations.telegram.auth import Auth
from integrations.telegram.commands import CommandRouter
from monitoring.audit_log import AuditLog
from utils.logger import get_logger

log = get_logger("telegram.handlers")

REFUSAL = "Accès refusé : vous n'êtes pas administrateur autorisé."
RATE_LIMITED = "Trop de commandes. Réessayez dans un instant."


def parse_command(text: str) -> Tuple[Optional[str], list]:
    """'/status@bot 5' -> ('status', ['5']). Non-commande -> (None, [])."""
    if not text:
        return None, []
    text = text.strip()
    if not text.startswith("/"):
        return None, []
    parts = text.split()
    cmd = parts[0][1:]
    if "@" in cmd:
        cmd = cmd.split("@", 1)[0]
    return cmd.lower(), parts[1:]


class UpdateHandler:
    def __init__(
        self,
        auth: Auth,
        router: CommandRouter,
        audit: AuditLog,
        client,
    ):
        self.auth = auth
        self.router = router
        self.audit = audit
        self.client = client

    def handle_message(self, user_id, chat_id, text: str) -> Optional[str]:
        command, args = parse_command(text)
        if command is None:
            return None  # on ignore les messages non-commande

        if not self.auth.is_admin(user_id):
            self.audit.record(user_id, command, args, allowed=False,
                              result="denied")
            log.warning(f"denied user={user_id} cmd=/{command}")
            self._reply(chat_id, REFUSAL)
            return REFUSAL

        if not self.auth.allow_rate(user_id):
            self.audit.record(user_id, command, args, allowed=False,
                              result="rate_limited")
            self._reply(chat_id, RATE_LIMITED)
            return RATE_LIMITED

        reply = self.router.dispatch(command, args, user_id)
        self.audit.record(user_id, command, args, allowed=True,
                          result=reply[:120])
        self._reply(chat_id, reply)
        return reply

    def handle_update(self, update: dict) -> Optional[str]:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id")
        user_id = msg.get("from", {}).get("id")
        return self.handle_message(user_id, chat_id, text)

    def _reply(self, chat_id, text: str) -> None:
        if self.client is not None and chat_id is not None:
            try:
                self.client.send_message(chat_id, text)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"reply failed: {exc}")
