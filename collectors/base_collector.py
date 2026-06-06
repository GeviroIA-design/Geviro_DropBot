from abc import ABC, abstractmethod
from typing import Any, List


class BaseCollector(ABC):
    """Contract minimal pour un collector.

    Deux modes :
      - collect() : retourne des items "neufs" (ex : marketplace).
      - enrich(items) : ajoute des champs à des items existants (ex : trends).
    Un collector implémente l'un OU l'autre.
    """

    name: str = "base"

    @abstractmethod
    def collect(self) -> List[Any]:
        ...

    def enrich(self, items: List[dict]) -> List[dict]:
        return items
