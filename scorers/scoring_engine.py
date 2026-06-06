from analyzers import competition_analyzer, demand_analyzer, trend_analyzer
from models.product import Product
from models.scorecard import Scorecard
from scorers.weights import DEFAULT_WEIGHTS, Weights
from utils.normalization import clamp, min_max, to_100


def compute_scorecard(p: Product, weights: Weights = DEFAULT_WEIGHTS) -> Scorecard:
    d = demand_analyzer.analyze(p)
    t = trend_analyzer.analyze(p)
    c = competition_analyzer.analyze(p)

    score_demande = to_100(d["demand_norm"])
    score_croissance = to_100(d["growth_norm"])
    score_momentum = to_100(t["momentum"])
    score_marge = to_100(clamp(p.net_margin / 0.4))
    score_roi = to_100(clamp(p.roi / 1.5))
    score_concurrence = to_100(c["competition_score"])
    score_saturation = to_100(c["saturation_score"])
    score_fournisseur = to_100(clamp(p.supplier_reliability))
    score_logistique = to_100(1.0 - min_max(p.shipping_delay_days, 5, 25))
    score_qualite = to_100(
        0.7 * clamp((p.average_rating - 3.0) / 2.0)
        + 0.3 * min_max(p.review_count, 0, 3000)
    )
    score_stabilite = to_100(p.demand_stability)
    score_risque = to_100(1.0 - p.risk_score)
    score_durabilite = to_100(p.durability_score)

    base = (
        weights.demande * score_demande
        + weights.croissance * score_croissance
        + weights.momentum * score_momentum
        + weights.marge * score_marge
        + weights.roi * score_roi
        + weights.concurrence * score_concurrence
        + weights.saturation * score_saturation
        + weights.fournisseur * score_fournisseur
        + weights.logistique * score_logistique
        + weights.qualite * score_qualite
        + weights.stabilite * score_stabilite
        + weights.risque * score_risque
        + weights.durabilite * score_durabilite
    ) / weights.total()

    bonus = 0.0
    malus = 0.0
    reasons: list[str] = []

    if t["breakout"] and p.demand_stability > 0.6:
        bonus += 5.0
        reasons.append("bonus breakout: momentum + stabilité élevée")

    if p.virality_score > 0.75 and p.durability_score < 0.55:
        malus += 6.0
        reasons.append("malus hype: viralité forte mais durabilité faible")

    if c["over_saturated"] and p.competition_level > 0.7:
        malus += 5.0
        reasons.append("malus saturation: marché trop dense")

    if p.shipping_delay_days > 18 and p.estimated_return_rate > 0.10:
        malus += 4.0
        reasons.append("malus logistique: délai long + retours élevés")

    final = max(0.0, min(100.0, base + bonus - malus))

    return Scorecard(
        product_id=p.product_id,
        score_demande=score_demande,
        score_croissance=score_croissance,
        score_momentum=score_momentum,
        score_marge=score_marge,
        score_roi=score_roi,
        score_concurrence=score_concurrence,
        score_saturation=score_saturation,
        score_fournisseur=score_fournisseur,
        score_logistique=score_logistique,
        score_qualite=score_qualite,
        score_stabilite=score_stabilite,
        score_risque=score_risque,
        score_durabilite=score_durabilite,
        bonus=round(bonus, 2),
        malus=round(malus, 2),
        final_score=round(final, 2),
        decision="WATCHLIST",
        reasons=reasons,
    )
