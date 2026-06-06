"""Envoi de notifications/alerts aux admins Telegram."""
from typing import List

from utils.logger import get_logger

log = get_logger("telegram.notifier")


class Notifier:
    def __init__(self, client, admin_ids: List[int]):
        self.client = client
        self.admin_ids = list(admin_ids)

    def broadcast(self, text: str) -> int:
        """Envoie `text` à tous les admins. Retourne le nb d'envois OK."""
        if self.client is None or not self.client.enabled:
            log.info(f"[notify-noop] {text}")
            return 0
        sent = 0
        for admin_id in self.admin_ids:
            try:
                if self.client.send_message(admin_id, text):
                    sent += 1
            except Exception as exc:  # noqa: BLE001
                log.warning(f"notify {admin_id} failed: {exc}")
        return sent
