"""Gestion des membres du bot (inscription + validation admin).

L'admin reste défini par l'environnement (TELEGRAM_ADMIN_IDS) et n'est JAMAIS
modifiable par le bot. Les membres (accès lecture) sont gérés ici, en base,
et validés par l'admin. Nombre de membres illimité.
"""
import time
from typing import Any, Dict, List, Optional

from runtime.service_state import Store

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
REVOKED = "revoked"


class MemberStore:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def get(self, user_id) -> Optional[Dict[str, Any]]:
        return self.store.query_one(
            "SELECT * FROM members WHERE user_id=?", (str(user_id),)
        )

    def status(self, user_id) -> Optional[str]:
        row = self.get(user_id)
        return row["status"] if row else None

    def is_approved(self, user_id) -> bool:
        return self.status(user_id) == APPROVED

    def request(self, user_id, name: str = "") -> bool:
        """Enregistre une demande si l'utilisateur est inconnu.
        Retourne True si une nouvelle demande a été créée."""
        if self.get(user_id) is not None:
            return False
        self.store.execute(
            "INSERT INTO members(user_id, name, status, requested_at) "
            "VALUES(?, ?, ?, ?)",
            (str(user_id), name or "", PENDING, self.clock()),
        )
        return True

    def _set(self, user_id, status: str, by) -> None:
        # upsert : l'admin peut pré-autoriser un id encore inconnu.
        now = self.clock()
        self.store.execute(
            "INSERT INTO members(user_id, name, status, requested_at, "
            "decided_at, decided_by) VALUES(?, '', ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET status=excluded.status, "
            "decided_at=excluded.decided_at, decided_by=excluded.decided_by",
            (str(user_id), status, now, now, str(by)),
        )

    def approve(self, user_id, by) -> None:
        self._set(user_id, APPROVED, by)

    def deny(self, user_id, by) -> None:
        self._set(user_id, DENIED, by)

    def revoke(self, user_id, by) -> None:
        self._set(user_id, REVOKED, by)

    def list(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if status:
            return self.store.query(
                "SELECT * FROM members WHERE status=? "
                "ORDER BY requested_at DESC LIMIT ?",
                (status, limit),
            )
        return self.store.query(
            "SELECT * FROM members ORDER BY requested_at DESC LIMIT ?", (limit,)
        )

    def count(self, status: str) -> int:
        row = self.store.query_one(
            "SELECT COUNT(*) AS n FROM members WHERE status=?", (status,)
        )
        return int(row["n"]) if row else 0
