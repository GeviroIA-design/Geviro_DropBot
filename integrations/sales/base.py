"""Abstraction d'un canal de vente (revente).

C'est LE point de branchement des vrais canaux (eBay, Shopify, ...).
Chaque canal réel implémentera `publish()` avec son API. Tant qu'aucun n'est
branché, on utilise `SimulatedSalesChannel` (aucune vente réelle).
"""
from abc import ABC, abstractmethod


class SalesChannel(ABC):
    name: str = "base"
    # True quand le canal effectue de VRAIES mises en vente.
    real: bool = False

    @abstractmethod
    def publish(self, proposal: dict) -> str:
        """Met le produit en vente. Retourne une référence d'annonce.

        `proposal` contient : product_id, name, supplier_cost, sell_price,
        platform_fee, margin_per_sale. Lève une exception si la publication
        échoue (l'executor la capte et marque la proposition 'failed').
        """
        ...
