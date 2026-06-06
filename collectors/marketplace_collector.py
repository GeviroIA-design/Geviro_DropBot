import random
from typing import List

from collectors.base_collector import BaseCollector

CATEGORIES = [
    "home", "beauty", "tech", "fitness",
    "pets", "kids", "outdoor", "kitchen",
]

NICHES = {
    "home": ["organisation", "decoration", "eclairage"],
    "beauty": ["skincare", "haircare", "outils"],
    "tech": ["accessoires", "gadgets", "audio"],
    "fitness": ["yoga", "musculation", "recovery"],
    "pets": ["chiens", "chats", "aquarium"],
    "kids": ["jeux", "apprentissage", "creatif"],
    "outdoor": ["camping", "velo", "voyage"],
    "kitchen": ["ustensiles", "boissons", "preparation"],
}


class MarketplaceCollector(BaseCollector):
    name = "marketplace"

    def __init__(self, n: int = 30, seed: int = 42):
        self.n = n
        self.rng = random.Random(seed)

    def collect(self) -> List[dict]:
        items: List[dict] = []
        for i in range(self.n):
            cat = self.rng.choice(CATEGORIES)
            niche = self.rng.choice(NICHES[cat])
            purchase = round(self.rng.uniform(2.5, 25.0), 2)
            multiplier = self.rng.uniform(2.2, 4.5)
            price = round(purchase * multiplier, 2)
            items.append(
                {
                    "product_id": f"P{i:04d}",
                    "name": f"{niche.title()} Item {i}",
                    "category": cat,
                    "niche": niche,
                    "purchase_cost": purchase,
                    "estimated_selling_price": price,
                    "shipping_cost": round(self.rng.uniform(1.5, 6.0), 2),
                    "ad_cost_estimate": round(self.rng.uniform(3.0, 12.0), 2),
                    "average_rating": round(self.rng.uniform(3.4, 4.9), 2),
                    "review_count": self.rng.randint(20, 5000),
                    "shipping_delay_days": self.rng.randint(6, 25),
                    "estimated_return_rate": round(
                        self.rng.uniform(0.01, 0.15), 3
                    ),
                }
            )
        return items
