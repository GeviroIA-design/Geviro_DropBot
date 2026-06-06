"""Exécution d'une proposition approuvée, SOUS GARDE-FOUS stricts.

C'est le seul endroit qui "dépense" : on y applique les plafonds.
`place_order` est le point de branchement de la VRAIE API marketplace
(CJ Dropshipping, etc.). Tant qu'aucune API réelle n'est branchée, l'ordre
est SIMULÉ et clairement signalé -> aucun argent réel n'est engagé.
"""
import time
from typing import Callable, Optional, Tuple

from models.enums import IncidentSeverity
from runtime.proposal_store import (
    EXECUTED, FAILED, PENDING, REJECTED, ProposalStore,
)
from utils.logger import get_logger

log = get_logger("executor")


class OrderExecutor:
    def __init__(
        self,
        proposals: ProposalStore,
        metrics,
        incidents,
        service_state,
        max_eur_per_order: float,
        max_orders_per_day: int,
        place_order: Optional[Callable[[dict], str]] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.proposals = proposals
        self.metrics = metrics
        self.incidents = incidents
        self.service_state = service_state
        self.max_eur_per_order = max_eur_per_order
        self.max_orders_per_day = max_orders_per_day
        # Par défaut : ordre SIMULÉ (aucune dépense réelle).
        self.place_order = place_order or self._simulated_order
        self.real_ordering = place_order is not None
        self.clock = clock

    @staticmethod
    def _simulated_order(proposal: dict) -> str:
        log.warning(
            f"COMMANDE SIMULEE (aucune API reelle branchee) : "
            f"{proposal['quantity']}x {proposal['product_id']} "
            f"pour {proposal['order_cost']:.2f} EUR"
        )
        return f"SIMULATED-{proposal['id']}"

    def reject(self, proposal_id: int, admin_id) -> Tuple[bool, str]:
        p = self.proposals.get(proposal_id)
        if p is None:
            return False, f"Proposition #{proposal_id} introuvable."
        if p["status"] != PENDING:
            return False, f"Proposition #{proposal_id} deja {p['status']}."
        self.proposals.set_status(proposal_id, REJECTED, decided_by=admin_id)
        return True, f"Proposition #{proposal_id} rejetee."

    def approve(self, proposal_id: int, admin_id) -> Tuple[bool, str]:
        p = self.proposals.get(proposal_id)
        if p is None:
            return False, f"Proposition #{proposal_id} introuvable."
        if p["status"] != PENDING:
            return False, f"Proposition #{proposal_id} deja {p['status']}."

        # --- GARDE-FOUS ---
        if self.service_state.is_safe_mode():
            return False, ("SAFE MODE actif (kill switch) : aucune execution. "
                          "Faites /safe_mode_off d'abord.")
        if p["order_cost"] > self.max_eur_per_order:
            return False, (
                f"Refuse : cout {p['order_cost']:.2f} EUR > plafond "
                f"{self.max_eur_per_order:.0f} EUR/commande."
            )
        day_ago = self.clock() - 86400.0
        if self.proposals.executed_since(day_ago) >= self.max_orders_per_day:
            return False, (
                f"Refuse : quota de {self.max_orders_per_day} commandes / 24h "
                f"atteint."
            )

        # --- EXECUTION ---
        try:
            ref = self.place_order(p)
        except Exception as exc:  # noqa: BLE001
            self.proposals.set_status(
                proposal_id, FAILED, decided_by=admin_id, note=str(exc)
            )
            self.incidents.record(
                IncidentSeverity.CRITICAL.value, "executor",
                f"echec commande proposition #{proposal_id}: {exc}",
            )
            return False, f"Echec de la commande : {exc}"

        self.proposals.set_status(
            proposal_id, EXECUTED, decided_by=admin_id, note=f"ref={ref}"
        )
        self.metrics.incr("orders_executed")
        self.metrics.incr("eur_spent", p["order_cost"])
        mode = "SIMULEE" if not self.real_ordering else "REELLE"
        return True, (
            f"Commande {mode} validee : #{proposal_id} "
            f"({p['quantity']}x {p['name']}) -> {p['order_cost']:.2f} EUR "
            f"(gain estime +{p['expected_gain']:.2f} EUR). ref={ref}"
        )
