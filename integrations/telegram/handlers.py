"""Traitement des updates Telegram : parsing, rôles, audit, dispatch, réponse.

Rôles :
- admin   : défini par l'environnement (TELEGRAM_ADMIN_IDS) -> accès total.
- membre  : approuvé par l'admin (en base) -> commandes de lecture seulement.
- inconnu : première interaction -> demande d'accès enregistrée + admin notifié.
- en attente / refusé : message d'information, pas d'accès.
"""
from typing import Optional, Tuple

from integrations.telegram.auth import Auth
from integrations.telegram.commands import MEMBER_COMMANDS, CommandRouter
from monitoring.audit_log import AuditLog
from utils.logger import get_logger

log = get_logger("telegram.handlers")

RATE_LIMITED = "Trop de commandes. Réessayez dans un instant."
MEMBER_FORBIDDEN = "Cette commande est réservée à l'administrateur."
REQUEST_SENT = (
    "Bienvenue 👋 Ta demande d'accès a été envoyée à l'administrateur. "
    "Tu seras prévenu dès qu'elle est validée."
)
PENDING_MSG = "Ta demande d'accès est en attente de validation par l'administrateur."
DENIED_MSG = "Ton accès n'a pas été autorisé par l'administrateur."


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
        members,
    ):
        self.auth = auth
        self.router = router
        self.audit = audit
        self.client = client
        self.members = members

    def handle_message(self, user_id, chat_id, text: str,
                       name: str = "") -> Optional[str]:
        command, args = parse_command(text)
        if command is None:
            return None  # on ignore les messages non-commande

        # --- ADMIN : accès total ---
        if self.auth.is_admin(user_id):
            return self._dispatch(user_id, chat_id, command, args)

        # --- MEMBRE approuvé : commandes de lecture uniquement ---
        if self.members.is_approved(user_id):
            if command not in MEMBER_COMMANDS:
                self.audit.record(user_id, command, args, allowed=False,
                                  result="member_forbidden")
                self._reply(chat_id, MEMBER_FORBIDDEN)
                return MEMBER_FORBIDDEN
            return self._dispatch(user_id, chat_id, command, args)

        # --- INCONNU / EN ATTENTE / REFUSÉ ---
        status = self.members.status(user_id)
        if status == "pending":
            self.audit.record(user_id, command, args, allowed=False,
                              result="pending")
            self._reply(chat_id, PENDING_MSG)
            return PENDING_MSG
        if status in ("denied", "revoked"):
            self.audit.record(user_id, command, args, allowed=False,
                              result=status)
            self._reply(chat_id, DENIED_MSG)
            return DENIED_MSG

        # nouvelle demande d'accès
        self.members.request(user_id, name)
        self.audit.record(user_id, command, args, allowed=False,
                          result="request_created")
        self._notify_admins(
            f"Nouvelle demande d'accès : {name or '?'} (id {user_id})\n"
            f"-> /accept {user_id}   ou   /deny {user_id}"
        )
        log.info(f"demande d'acces user={user_id} ({name})")
        self._reply(chat_id, REQUEST_SENT)
        return REQUEST_SENT

    def _dispatch(self, user_id, chat_id, command, args) -> str:
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
        frm = msg.get("from", {})
        user_id = frm.get("id")
        name = frm.get("first_name") or frm.get("username") or ""
        return self.handle_message(user_id, chat_id, text, name)

    def _notify_admins(self, text: str) -> None:
        for admin_id in self.auth.admin_ids:
            try:
                self.client.send_message(admin_id, text)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"notify admin {admin_id} failed: {exc}")

    def _reply(self, chat_id, text: str) -> None:
        if self.client is not None and chat_id is not None:
            try:
                self.client.send_message(chat_id, text)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"reply failed: {exc}")
