import random
from typing import List

from collectors.base_collector import BaseCollector


class CompetitorCollector(BaseCollector):
    name = "competitor"

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed + 3)

    def collect(self) -> List[dict]:
        return []

    def enrich(self, items: List[dict]) -> List[dict]:
        for p in items:
            p["competition_level"] = round(self.rng.uniform(0.05, 0.95), 3)
            p["market_saturation"] = round(self.rng.uniform(0.05, 0.95), 3)
        return items
