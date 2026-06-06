"""Journal d'audit des actions admin Telegram."""
import json
import time
from typing import Any, Dict, List, Optional

from runtime.service_state import Store


class AuditLog:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def record(
        self,
        admin_id: Any,
        command: str,
        args: Optional[list] = None,
        allowed: bool = True,
        result: str = "",
    ) -> int:
        return self.store.execute(
            "INSERT INTO audit(ts, admin_id, command, args, allowed, result) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (
                self.clock(),
                str(admin_id),
                command,
                json.dumps(args or []),
                1 if allowed else 0,
                result[:500],
            ),
        )

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.store.query(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        )
