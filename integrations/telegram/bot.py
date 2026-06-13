"""Client Telegram minimal basé sur urllib (stdlib, zéro dépendance).

Implémente uniquement getUpdates (long polling) et sendMessage.
Si aucun token n'est configuré, le client est 'disabled' et toutes les
opérations sont des no-op sûrs.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("telegram.client")

_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient:
    def __init__(self, token: str, poll_timeout: int = 30):
        self.token = token or ""
        self.poll_timeout = poll_timeout
        self.enabled = bool(self.token)

    def _call(self, method: str, params: dict, timeout: float) -> Optional[dict]:
        if not self.enabled:
            return None
        url = _API.format(token=self.token, method=method)
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            payload = json.loads(body)
            if not payload.get("ok"):
                log.warning(f"telegram {method} not ok: {payload.get('description')}")
                return None
            return payload
        except urllib.error.URLError as exc:
            log.warning(f"telegram {method} network error: {exc}")
            return None
        except (ValueError, TimeoutError) as exc:
            log.warning(f"telegram {method} error: {exc}")
            return None

    def get_updates(self, offset: int) -> List[Dict[str, Any]]:
        payload = self._call(
            "getUpdates",
            {"offset": offset, "timeout": self.poll_timeout},
            timeout=self.poll_timeout + 10,
        )
        if not payload:
            return []
        return payload.get("result", [])

    def send_message(self, chat_id: Any, text: str) -> bool:
        # Telegram limite à ~4096 caractères par message.
        text = text[:4000]
        payload = self._call(
            "sendMessage",
            {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"},
            timeout=20,
        )
        return payload is not None

    def set_my_commands(self, commands: List[Dict[str, str]],
                        scope: Optional[dict] = None) -> bool:
        """Enregistre le menu des commandes (autocomplétion '/' dans Telegram).

        `commands` : [{"command": "status", "description": "..."}, ...].
        `scope` (optionnel) : portée Telegram, ex. {"type": "default"} (tous)
        ou {"type": "chat", "chat_id": <id>} (un chat précis -> menu privé).
        """
        params = {"commands": json.dumps(commands, ensure_ascii=False)}
        if scope is not None:
            params["scope"] = json.dumps(scope)
        payload = self._call("setMyCommands", params, timeout=15)
        return payload is not None
