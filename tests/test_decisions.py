import unittest

from analyzers import financial_analyzer, risk_analyzer
from models.product import Product
from scorers.decision_rules import decide
from scorers.scoring_engine import compute_scorecard


def _p(**kw) -> Product:
    base = dict(
        product_id="T1", name="Test", category="home", niche="x",
        purchase_cost=4.0, estimated_selling_price=28.0, shipping_cost=2.0,
        ad_cost_estimate=3.0, demand_volume=20000, demand_growth=0.5,
        short_term_momentum=0.6, mid_term_momentum=0.4,
        competition_level=0.25, market_saturation=0.3,
        average_rating=4.7, review_count=900,
        shipping_delay_days=8, supplier_reliability=0.92,
        estimated_return_rate=0.03, seasonality_score=0.3,
        demand_stability=0.85, virality_score=0.4, durability_score=0.8,
    )
    base.update(kw)
    return Product(**base)


def _run(p: Product):
    p = financial_analyzer.analyze(p)
    p = risk_analyzer.analyze(p)
    sc = compute_scorecard(p)
    return p, decide(p, sc)


class TestDecisions(unittest.TestCase):
    def test_strong_product_buys_or_tests(self):
        _, sc = _run(_p())
        self.assertIn(sc.decision, ("BUY", "TEST"))

    def test_unreliable_supplier_blocks_buy(self):
        _, sc = _run(_p(supplier_reliability=0.5))
        self.assertNotEqual(sc.decision, "BUY")

    def test_oversaturated_blocks_buy(self):
        _, sc = _run(_p(market_saturation=0.92, competition_level=0.85))
        self.assertNotEqual(sc.decision, "BUY")

    def test_low_margin_blocks_buy(self):
        _, sc = _run(
            _p(purchase_cost=20.0, estimated_selling_price=25.0, ad_cost_estimate=6.0)
        )
        self.assertNotEqual(sc.decision, "BUY")

    def test_hype_unstable_blocks_buy(self):
        _, sc = _run(_p(virality_score=0.9, durability_score=0.3))
        self.assertNotEqual(sc.decision, "BUY")

    def test_terrible_product_rejects(self):
        _, sc = _run(
            _p(
                purchase_cost=22.0,
                estimated_selling_price=24.0,
                supplier_reliability=0.42,
                market_saturation=0.95,
                competition_level=0.9,
                average_rating=3.4,
                shipping_delay_days=24,
                estimated_return_rate=0.18,
                demand_volume=400,
                demand_growth=-0.2,
                short_term_momentum=-0.25,
                mid_term_momentum=-0.15,
                demand_stability=0.25,
                durability_score=0.3,
            )
        )
        self.assertEqual(sc.decision, "REJECT")

    def test_decision_is_one_of_four(self):
        _, sc = _run(_p())
        self.assertIn(sc.decision, {"BUY", "TEST", "WATCHLIST", "REJECT"})


if __name__ == "__main__":
    unittest.main()
