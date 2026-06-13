"""Stockage des propositions de REVENTE (table `proposals`).

Une proposition = un produit à marge positive que le bot soumet à l'admin
pour validation Telegram. Sur /approve, le produit est MIS EN VENTE
(publié) sur le canal de vente — aucun achat, aucun stock.
"""
import time
from typing import Any, Dict, List, Optional

from runtime.service_state import Store

PENDING = "pending"
LISTED = "listed"
REJECTED = "rejected"
FAILED = "failed"


class ProposalStore:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def create(
        self,
        product_id: str,
        name: str,
        supplier_cost: float,
        sell_price: float,
        platform_fee: float,
        margin_per_sale: float,
        score: float,
        product_url: str = "",
    ) -> int:
        return self.store.execute(
            "INSERT INTO proposals(product_id, name, supplier_cost, sell_price, "
            "platform_fee, margin_per_sale, score, product_url, status, "
            "created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product_id, name, supplier_cost, sell_price, platform_fee,
                margin_per_sale, score, product_url, PENDING, self.clock(),
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

    def list_listings(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.list(status=LISTED, limit=limit)

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

    def set_listed(
        self, proposal_id: int, channel: str, listing_ref: str, decided_by: Any
    ) -> None:
        self.store.execute(
            "UPDATE proposals SET status=?, channel=?, listing_ref=?, "
            "decided_at=?, decided_by=? WHERE id=?",
            (LISTED, channel, listing_ref, self.clock(),
             str(decided_by), proposal_id),
        )

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

    def listed_since(self, ts: float) -> int:
        row = self.store.query_one(
            "SELECT COUNT(*) AS n FROM proposals WHERE status=? AND decided_at>=?",
            (LISTED, ts),
        )
        return int(row["n"]) if row else 0
