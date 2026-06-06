from models.product import Product
from utils.normalization import clamp, min_max


def analyze(p: Product) -> dict:
    return {
        "demand_norm": min_max(p.demand_volume, 0, 50000),
        "growth_norm": clamp((p.demand_growth + 0.3) / 1.2),
        "stability": clamp(p.demand_stability),
    }
