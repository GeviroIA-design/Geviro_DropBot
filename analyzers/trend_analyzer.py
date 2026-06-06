from models.product import Product
from utils.normalization import clamp


def analyze(p: Product) -> dict:
    short = clamp((p.short_term_momentum + 0.3) / 1.25)
    mid = clamp((p.mid_term_momentum + 0.2) / 1.0)
    momentum = clamp(0.6 * short + 0.4 * mid)
    breakout = momentum > 0.7 and p.demand_stability > 0.6
    return {"momentum": momentum, "short": short, "mid": mid, "breakout": breakout}
