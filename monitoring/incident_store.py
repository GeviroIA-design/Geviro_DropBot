"""Stockage des incidents avec acquittement."""
import time
from typing import Any, Dict, List, Optional

from models.enums import IncidentSeverity
from runtime.service_state import Store


class IncidentStore:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def record(self, severity: str, source: str, message: str) -> int:
        if isinstance(severity, IncidentSeverity):
            severity = severity.value
        return self.store.execute(
            "INSERT INTO incidents(severity, source, message, created_at, "
            "acknowledged) VALUES(?, ?, ?, ?, 0)",
            (severity, source, message, self.clock()),
        )

    def list(
        self, limit: int = 20, only_open: bool = False
    ) -> List[Dict[str, Any]]:
        if only_open:
            return self.store.query(
                "SELECT * FROM incidents WHERE acknowledged=0 "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        return self.store.query(
            "SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)
        )

    def open_count(self) -> int:
        row = self.store.query_one(
            "SELECT COUNT(*) AS n FROM incidents WHERE acknowledged=0"
        )
        return int(row["n"]) if row else 0

    def ack(self, incident_id: int, admin_id: str) -> bool:
        rid = self.store.execute(
            "UPDATE incidents SET acknowledged=1, acknowledged_by=?, "
            "acknowledged_at=? WHERE id=? AND acknowledged=0",
            (str(admin_id), self.clock(), incident_id),
        )
        # rowcount via vérification d'existence acquittée
        row = self.store.query_one(
            "SELECT acknowledged FROM incidents WHERE id=?", (incident_id,)
        )
        return bool(row and row["acknowledged"] == 1)

    def get(self, incident_id: int) -> Optional[Dict[str, Any]]:
        return self.store.query_one(
            "SELECT * FROM incidents WHERE id=?", (incident_id,)
        )
