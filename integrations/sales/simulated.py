"""Canal de vente SIMULÉ : aucune vente réelle, aucun compte requis.

Permet de tester toute la boucle revente (proposition -> /approve -> mise en
vente -> suivi) dans Telegram, en attendant le branchement d'eBay.
"""
from integrations.sales.base import SalesChannel
from utils.logger import get_logger

log = get_logger("sales.simulated")


class SimulatedSalesChannel(SalesChannel):
    name = "simulated"
    real = False

    def publish(self, proposal: dict) -> str:
        log.warning(
            "MISE EN VENTE SIMULEE (aucun canal reel branche) : "
            f"{proposal['name']} a {proposal['sell_price']:.2f} EUR "
            f"(marge +{proposal['margin_per_sale']:.2f}/vente)"
        )
        return f"SIM-LISTING-{proposal['id']}"
