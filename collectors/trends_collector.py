import random
from typing import List

from collectors.base_collector import BaseCollector


class TrendsCollector(BaseCollector):
    """Simule des signaux de demande / momentum / stabilité."""

    name = "trends"

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed + 1)

    def collect(self) -> List[dict]:
        return []

    def enrich(self, items: List[dict]) -> List[dict]:
        for p in items:
            p["demand_volume"] = self.rng.randint(500, 50000)
            p["demand_growth"] = round(self.rng.uniform(-0.25, 0.9), 3)
            p["short_term_momentum"] = round(self.rng.uniform(-0.3, 0.95), 3)
            p["mid_term_momentum"] = round(self.rng.uniform(-0.2, 0.8), 3)
            p["seasonality_score"] = round(self.rng.uniform(0.0, 1.0), 3)
            p["demand_stability"] = round(self.rng.uniform(0.2, 0.95), 3)
            p["virality_score"] = round(self.rng.uniform(0.0, 1.0), 3)
            p["durability_score"] = round(self.rng.uniform(0.2, 0.95), 3)
        return items
