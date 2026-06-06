from models.product import Product
from utils.normalization import clamp


def analyze(p: Product) -> dict:
    competition_score = clamp(1.0 - p.competition_level)
    saturation_score = clamp(1.0 - p.market_saturation)
    over_saturated = p.market_saturation > 0.8
    return {
        "competition_score": competition_score,
        "saturation_score": saturation_score,
        "over_saturated": over_saturated,
    }
