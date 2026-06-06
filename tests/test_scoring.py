import unittest

from analyzers import financial_analyzer, risk_analyzer
from models.product import Product
from scorers.scoring_engine import compute_scorecard


def _p(**kw) -> Product:
    base = dict(
        product_id="T1", name="Test", category="home", niche="x",
        purchase_cost=5.0, estimated_selling_price=25.0, shipping_cost=2.0,
        ad_cost_estimate=3.0, demand_volume=15000, demand_growth=0.4,
        short_term_momentum=0.5, mid_term_momentum=0.3,
        competition_level=0.3, market_saturation=0.3,
        average_rating=4.6, review_count=800,
        shipping_delay_days=9, supplier_reliability=0.9,
        estimated_return_rate=0.04, seasonality_score=0.3,
        demand_stability=0.8, virality_score=0.4, durability_score=0.75,
    )
    base.update(kw)
    return Product(**base)


def _prepared(**kw) -> Product:
    p = _p(**kw)
    p = financial_analyzer.analyze(p)
    return risk_analyzer.analyze(p)


class TestScoring(unittest.TestCase):
    def test_score_range(self):
        sc = compute_scorecard(_prepared())
        self.assertGreaterEqual(sc.final_score, 0)
        self.assertLessEqual(sc.final_score, 100)

    def test_high_quality_outperforms_low(self):
        good = compute_scorecard(_prepared())
        bad = compute_scorecard(
            _prepared(
                supplier_reliability=0.45,
                market_saturation=0.92,
                estimated_return_rate=0.18,
                average_rating=3.4,
                shipping_delay_days=22,
                competition_level=0.85,
            )
        )
        self.assertGreater(good.final_score, bad.final_score)

    def test_hype_malus_applied(self):
        sc = compute_scorecard(
            _prepared(virality_score=0.9, durability_score=0.3)
        )
        self.assertTrue(any("hype" in r for r in sc.reasons))
        self.assertGreater(sc.malus, 0)

    def test_breakout_bonus_applied(self):
        sc = compute_scorecard(
            _prepared(
                short_term_momentum=0.9,
                mid_term_momentum=0.6,
                demand_stability=0.85,
            )
        )
        self.assertTrue(any("breakout" in r for r in sc.reasons))
        self.assertGreater(sc.bonus, 0)

    def test_saturation_malus(self):
        sc = compute_scorecard(
            _prepared(market_saturation=0.9, competition_level=0.85)
        )
        self.assertTrue(any("saturation" in r for r in sc.reasons))

    def test_subscores_in_range(self):
        sc = compute_scorecard(_prepared())
        for attr in (
            "score_demande", "score_croissance", "score_momentum",
            "score_marge", "score_roi", "score_concurrence",
            "score_saturation", "score_fournisseur", "score_logistique",
            "score_qualite", "score_stabilite", "score_risque",
            "score_durabilite",
        ):
            v = getattr(sc, attr)
            self.assertGreaterEqual(v, 0, attr)
            self.assertLessEqual(v, 100, attr)


if __name__ == "__main__":
    unittest.main()
