"""Stockage des propositions d'achat (table `proposals`).

Une proposition = une opportunité à gain positif que le bot soumet à
l'admin pour validation Telegram avant toute exécution.
"""
import time
from typing import Any, Dict, List, Optional

from runtime.service_state import Store

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXECUTED = "executed"
FAILED = "failed"


class ProposalStore:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def create(
        self,
        product_id: str,
        name: str,
        quantity: int,
        unit_cost: float,
        unit_sell_price: float,
        expected_unit_net: float,
        expected_gain: float,
        order_cost: float,
        score: float,
    ) -> int:
        return self.store.execute(
            "INSERT INTO proposals(product_id, name, quantity, unit_cost, "
            "unit_sell_price, expected_unit_net, expected_gain, order_cost, "
            "score, status, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product_id, name, quantity, unit_cost, unit_sell_price,
                expected_unit_net, expected_gain, order_cost, score,
                PENDING, self.clock(),
            ),
        )

    def get(self, proposal_id: int) -> Optional[Dict[str, Any]]:
        return self.store.query_one(
            "SELECT * FROM proposals WHERE id=?", (proposal_id,)
        )

    def list(
        self, status: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        if status:
            return self.store.query(
                "SELECT * FROM proposals WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit),
            )
        return self.store.query(
            "SELECT * FROM proposals ORDER BY id DESC LIMIT ?", (limit,)
        )

    def has_pending_for(self, product_id: str) -> bool:
        row = self.store.query_one(
            "SELECT 1 FROM proposals WHERE product_id=? AND status=? LIMIT 1",
            (product_id, PENDING),
        )
        return row is not None

    def pending_count(self) -> int:
        row = self.store.query_one(
            "SELECT COUNT(*) AS n FROM proposals WHERE status=?", (PENDING,)
        )
        return int(row["n"]) if row else 0

    def set_status(
        self, proposal_id: int, status: str,
        decided_by: Optional[Any] = None, note: Optional[str] = None,
    ) -> None:
        self.store.execute(
            "UPDATE proposals SET status=?, decided_at=?, decided_by=?, note=? "
            "WHERE id=?",
            (
                status, self.clock(),
                str(decided_by) if decided_by is not None else None,
                note, proposal_id,
            ),
        )

    def executed_since(self, ts: float) -> int:
        row = self.store.query_one(
            "SELECT COUNT(*) AS n FROM proposals WHERE status=? AND decided_at>=?",
            (EXECUTED, ts),
        )
        return int(row["n"]) if row else 0
