"""Gestion des alertes : enregistre un incident + notifie (avec anti-spam)."""
import time
from typing import Callable, Dict, Optional

from models.enums import IncidentSeverity
from monitoring.incident_store import IncidentStore
from utils.logger import get_logger

log = get_logger("alerts")

_SEVERITY_ORDER = {
    IncidentSeverity.INFO.value: 0,
    IncidentSeverity.WARNING.value: 1,
    IncidentSeverity.CRITICAL.value: 2,
}


class AlertManager:
    def __init__(
        self,
        incidents: IncidentStore,
        notify: Optional[Callable[[str], int]] = None,
        notify_min_severity: str = IncidentSeverity.WARNING.value,
        dedup_window: float = 300.0,
        clock: Callable[[], float] = time.time,
    ):
        self.incidents = incidents
        self.notify = notify
        self.notify_min_severity = notify_min_severity
        self.dedup_window = dedup_window
        self.clock = clock
        self._last_sent: Dict[str, float] = {}

    def set_notifier(self, notify: Callable[[str], int]) -> None:
        self.notify = notify

    def _should_notify(self, severity: str, key: str) -> bool:
        if _SEVERITY_ORDER.get(severity, 0) < _SEVERITY_ORDER.get(
            self.notify_min_severity, 1
        ):
            return False
        now = self.clock()
        last = self._last_sent.get(key)
        if last is not None and (now - last) < self.dedup_window:
            return False
        self._last_sent[key] = now
        return True

    def raise_alert(self, severity: str, source: str, message: str) -> int:
        if isinstance(severity, IncidentSeverity):
            severity = severity.value
        incident_id = self.incidents.record(severity, source, message)
        log.warning(f"[{severity}] {source}: {message}")
        if self.notify and self._should_notify(severity, f"{source}:{message}"):
            sev_fr = {
                "info": "INFO", "warning": "AVERTISSEMENT", "critical": "CRITIQUE",
            }.get(severity, severity.upper())
            src_fr = {
                "watchdog": "surveillance", "executor": "exécution",
                "admin": "admin", "recovery": "redémarrage", "worker": "ouvrier",
            }.get(source, source)
            try:
                self.notify(f"[{sev_fr}] {src_fr} : {message}")
            except Exception as exc:  # noqa: BLE001
                log.warning(f"alert notify failed: {exc}")
        return incident_id
