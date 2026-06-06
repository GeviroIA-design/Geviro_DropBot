import random
from typing import List

from collectors.base_collector import BaseCollector


class SupplierCollector(BaseCollector):
    name = "supplier"

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed + 2)

    def collect(self) -> List[dict]:
        return []

    def enrich(self, items: List[dict]) -> List[dict]:
        for p in items:
            p["supplier_reliability"] = round(self.rng.uniform(0.4, 0.98), 3)
        return items
