"""Console d'administration Telegram : assemble client + auth + handlers
et tourne en boucle de long-polling. Branche aussi le notifier d'alertes.
"""
import threading
from typing import Optional

from config.settings import Settings, settings as default_settings
from integrations.telegram.auth import Auth
from integrations.telegram.bot import TelegramClient
from integrations.telegram.commands import CommandRouter
from integrations.telegram.handlers import UpdateHandler
from integrations.telegram.notifier import Notifier
from utils.logger import get_logger

log = get_logger("telegram.admin")


class TelegramAdmin:
    def __init__(self, supervisor, settings: Settings = default_settings,
                 client: Optional[TelegramClient] = None):
        self.supervisor = supervisor
        self.settings = settings
        self.client = client or TelegramClient(
            settings.telegram_bot_token, settings.telegram_poll_timeout
        )
        self.auth = Auth(
            settings.telegram_admin_ids,
            rate_limit=settings.telegram_rate_limit,
        )
        # Permet à /reload_config de mettre à jour l'allowlist.
        supervisor.auth = self.auth
        self.router = CommandRouter(supervisor)
        self.handler = UpdateHandler(
            self.auth, self.router, supervisor.audit, self.client
        )
        self.notifier = Notifier(self.client, settings.telegram_admin_ids)
        supervisor.alerts.set_notifier(self.notifier.broadcast)
        # Push des propositions d'achat vers l'admin.
        supervisor.notify = self.notifier.broadcast

        self.enabled = self.client.enabled
        self._offset = 0

    def poll_once(self) -> int:
        updates = self.client.get_updates(self._offset)
        for u in updates:
            self._offset = max(self._offset, u.get("update_id", 0) + 1)
            try:
                self.handler.handle_update(u)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"update handling error: {exc}")
        return len(updates)

    def run(self, stop_event: threading.Event) -> None:
        if not self.enabled:
            log.info("telegram desactive (aucun token) -- console admin off")
            return
        if not self.settings.telegram_admin_ids:
            log.warning("telegram actif mais AUCUN admin -- tout sera refuse")
        log.info("telegram admin: polling demarre")
        while not stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001
                log.warning(f"poll loop error: {exc}")
                stop_event.wait(3.0)
        log.info("telegram admin: polling arrete")
