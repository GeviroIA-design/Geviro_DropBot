from models.product import Product
from utils.normalization import clamp, min_max


def analyze(p: Product) -> Product:
    """Risk composite (0 = safe, 1 = très risqué)."""
    return_risk = min_max(p.estimated_return_rate, 0.0, 0.2)
    supplier_risk = 1.0 - clamp(p.supplier_reliability)
    logistic_risk = min_max(p.shipping_delay_days, 5, 25)
    saturation_risk = clamp(p.market_saturation)
    quality_risk = 1.0 - clamp((p.average_rating - 3.0) / 2.0)
    hype_risk = max(0.0, p.virality_score - p.durability_score)

    risk = (
        0.25 * return_risk
        + 0.25 * supplier_risk
        + 0.15 * logistic_risk
        + 0.15 * saturation_risk
        + 0.10 * quality_risk
        + 0.10 * hype_risk
    )
    p.risk_score = round(clamp(risk), 4)
    return p
