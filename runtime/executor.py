"""Exécution d'une proposition approuvée = MISE EN VENTE (revente), sous
garde-fous. Aucun achat, aucun stock : le bot publie le produit sur le canal
de vente. La vente réelle dépend du canal (eBay, ...) et du trafic.

`channel.publish` est le point de branchement du vrai canal. Tant qu'un canal
simulé est utilisé, aucune vente réelle n'a lieu.
"""
import time
from typing import Callable, Tuple

from models.enums import IncidentSeverity
from runtime.proposal_store import FAILED, PENDING, REJECTED, ProposalStore
from utils.logger import get_logger

log = get_logger("executor")


class ResaleExecutor:
    def __init__(
        self,
        proposals: ProposalStore,
        metrics,
        incidents,
        service_state,
        channel,
        min_margin_eur: float,
        max_listings_per_day: int,
        clock: Callable[[], float] = time.time,
    ):
        self.proposals = proposals
        self.metrics = metrics
        self.incidents = incidents
        self.service_state = service_state
        self.channel = channel
        self.min_margin_eur = min_margin_eur
        self.max_listings_per_day = max_listings_per_day
        self.clock = clock

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
            return False, ("SAFE MODE actif (kill switch) : aucune mise en "
                          "vente. Faites /safe_mode_off d'abord.")
        if p["margin_per_sale"] < self.min_margin_eur:
            return False, (
                f"Refuse : marge {p['margin_per_sale']:.2f} EUR < minimum "
                f"{self.min_margin_eur:.2f} EUR/vente."
            )
        day_ago = self.clock() - 86400.0
        if self.proposals.listed_since(day_ago) >= self.max_listings_per_day:
            return False, (
                f"Refuse : quota de {self.max_listings_per_day} mises en vente "
                f"/ 24h atteint."
            )

        # --- MISE EN VENTE (publication sur le canal) ---
        try:
            ref = self.channel.publish(p)
        except Exception as exc:  # noqa: BLE001
            self.proposals.set_status(
                proposal_id, FAILED, decided_by=admin_id, note=str(exc)
            )
            self.incidents.record(
                IncidentSeverity.CRITICAL.value, "executor",
                f"echec mise en vente proposition #{proposal_id}: {exc}",
            )
            return False, f"Echec de la mise en vente : {exc}"

        self.proposals.set_listed(proposal_id, self.channel.name, ref, admin_id)
        self.metrics.incr("listings_published")
        mode = "REELLE" if getattr(self.channel, "real", False) else "SIMULEE"
        return True, (
            f"Mise en vente {mode} : #{proposal_id} ({p['name']}) sur "
            f"{self.channel.name} a {p['sell_price']:.2f} EUR "
            f"(marge +{p['margin_per_sale']:.2f}/vente). ref={ref}"
        )
